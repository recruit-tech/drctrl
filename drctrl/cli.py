#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import contextlib

import click
import yaml
import functools
import datarobot as dr
import pandas as pd
import pyaml

from drctrl.lib.ConfigParser import configParser
from drctrl.lib.Exceptions import NotSpecifiedValidParam
from drctrl.lib import Utils
from drctrl.lib.Project import Project
from drctrl.plugins.base import IOManager

_global_options = [
    click.option(
        'credential',
        '--credential',
        envvar='DR_CREDENTIAL',
        default='~/.config/datarobot/drconfig.yaml',
        type=click.Path()),
]

def share_option(func):
    for option in reversed(_global_options):
        func = option(func)

    @functools.wraps(func)
    def preprocess(*args, **kwargs):
        ctx = args[0]
        ctx.obj['credential'] = load_credential(kwargs['credential'])
        credential = ctx.obj['credential']

        # initialize
        dr.Client(token=credential['token'], endpoint=credential['endpoint'])

        func(*args, **kwargs)

    return preprocess


def share_config(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        ctx = args[0]
        config_path = kwargs['config_path']
        if 'config' not in ctx.obj:
            config = configParser(config_path)

            ctx.obj['config'] = config

        func(*args, **kwargs)

    return wrapper

def load_credential(path):
    # give priority to environment variables
    if 'DR_TOKEN' in os.environ and 'DR_ENDPOINT' in os.environ:
        credential = {
                'token'    : os.environ['DR_TOKEN'],
                'endpoint' : os.environ['DR_ENDPOINT'],
        }
    else:
        path = os.path.expanduser(path)
        credential = yaml.load(open(path, 'r'))
    return credential

@click.group()
@click.pass_context
@share_option
def cli(ctx, credential):
    pass


@cli.command(help='Apply all commands in configuration file')
@click.pass_context
@click.argument('config_path', nargs=1, type=click.Path(exists=True), metavar='</path/to/configuration-file>')
@share_option
@share_config
def apply(
        ctx,
        credential,  # shared options
        config_path):
    config = ctx.obj['config']

    if not config.is_valid():
        raise Exception('configuration file error')

    has_fit = config.get_params(cmd='fit') is not None
    has_frozen = config.get_params(cmd='frozen') is not None
    has_pred = config.get_params(cmd='predict') is not None

    with section('Apply setting'):
        if not has_fit and has_pred:
            config.set_params(cmd='environment',
                    params={'autopilot': 'fullauto', 'wait_for_completion': 'True'})

        ctx.forward(build)
        project = ctx.obj['project']
        config.set_params(cmd='environment',
                params={'project_id': project.project_id})

        if has_fit:
            if has_pred or has_frozen:
                config.set_params(cmd='fit',
                        params={'wait_for_completion': True})
            ctx.forward(fit)

        if has_frozen:
            if config.get_param(cmd='frozen', param='model_id') is None:
                if has_fit:
                    config.set_params(cmd='frozen',
                            params={'model_id': ctx.obj['model_id']})
            ctx.forward(frozen)

        if has_pred:
            if config.get_param(cmd='pred', param='model_id') is None:
                if has_fit or has_frozen:
                    config.set_params(cmd='predict',
                            params={'model_id': ctx.obj['model_id']})
            ctx.forward(predict)


# build project
@cli.command(help='building project with given configuration file')
@click.pass_context
@click.argument('config_path', nargs=1, type=click.Path(exists=True), metavar='</path/to/configuration-file>')
@share_option
@share_config
def build(
        ctx,
        credential,  # shared options
        config_path):
    config = ctx.obj['config']

    if not config.is_valid():
        raise Exception('configuration file error')

    with section('Build project'):
        project = Project(**config.get_params(cmd='environment'))
        if project.project_id is None:
            if project.project_name is None:
                project.project_name = Utils.get_currenttime_string()
            df = IOManager(io_type='input', io_params=config.get_param(cmd='environment', param='dataset')).to_df()
            project.build_project(df)

        # set params for successor process
        ctx.obj['project'] = project

    click.echo('project building is succeed')
    click.echo(f"project name: {project.project_name}, project_id: {project.project_id}")


@cli.command(help='training model with given configuration file')
@click.pass_context
@click.argument('config_path', nargs=1, type=click.Path(exists=True), metavar='</path/to/configuration-file>')
@share_option
@share_config
def fit(
        ctx,
        credential,  # shared options
        config_path):
    config = ctx.obj['config']
    cmd='fit'

    if not config.is_valid(cmds=[cmd]):
        raise Exception('configuration file error')

    project = Project(**config.get_params(cmd='environment'))
    if not hasattr(project, 'dr_project') or project.dr_project is None:
        raise NotSpecifiedValidParam('project id is not supplied. you should run build command befor, or apply command')

    with section("Training"):
        featurelist_name, model_type = project.fit(**config.get_params(cmd))

        # set params for successor process
        ctx.obj['featurelist_name'] = featurelist_name
        if model_type == 'autopilot':
            sort_key = Utils.get_appropriate_dataset(project.cv_method, project.validation_type,
                                                     project.validation_params)
            ctx.obj['model_id'] = project.search_models(featurelist_name=featurelist_name, sort_key=sort_key)[0].id
        else:
            ctx.obj['model_id'] = config.get_param(cmd, param='model_id')

    click.echo("fit command is succeed.")
    click.echo(f"'{model_type}' with featurelist: '{featurelist_name}'")
    click.echo(f"model_id: {ctx.obj['model_id']}")


@cli.command(help='freezing model with given configuration file')
@click.pass_context
@click.argument('config_path', nargs=1, type=click.Path(exists=True), metavar='</path/to/configuration-file>')
@share_option
@share_config
def frozen(
        ctx,
        credential,  # shared options
        config_path):
    config = ctx.obj['config']
    cmd = 'frozen'

    if not config.is_valid(cmds=[cmd]):
        raise Exception('configuration file error')

    project = Project(**config.get_params(cmd='environment'))
    if not hasattr(project, 'dr_project') or project.dr_project is None:
        raise NotSpecifiedValidParam('project id is not supplied. you should run build command befor, or apply command')

    model_id = config.get_param(cmd, param='model_id')

    with section('Freezing model'):
        if model_id is None:
            sort_key = Utils.get_appropriate_dataset(project.cv_method, project.validation_type,
                                                     project.validation_params)
            model = project.search_models(sort_key=sort_key)[0]
            model_id = model.id
        config.set_params(cmd, params={'model_id' : model_id})

        new_model_id = project.frozen(**config.get_params(cmd))
        ctx.obj['model_id'] = new_model_id

    click.echo('frozen command is succeed.')
    click.echo(f"'{model_id}' is frozen -> new model_id: {new_model_id}")


@cli.command(help='predicting with given configuration file')
@click.pass_context
@click.argument('config_path', nargs=1, type=click.Path(exists=True), metavar='</path/to/configuration-file>')
@share_option
@share_config
def predict(
        ctx,
        credential,  # shared options
        config_path):
    cmd = 'predict'
    config = ctx.obj['config']

    if not config.is_valid(cmds=[cmd]):
        raise Exception('configuration file error')

    project = Project(**config.get_params(cmd='environment'))
    if not hasattr(project, 'dr_project') or project.dr_project is None:
        raise NotSpecifiedValidParam('project id is not supplied. you should run build command befor, or apply command')

    prediction_column = Utils.get_appropriate_prediction_column(project.dr_project.target_type)

    params = config.get_params(cmd)
    model_id = config.get_param(cmd, param='model_id')

    with section('Upload dataset'):
        input_df = IOManager(io_type='input', io_params=config.get_param(cmd, param='input')).to_df()
        dataset = project.upload_dataset(input_df)
        click.echo(f"#rows: {dataset.num_rows}, #columns: {dataset.num_columns}")

    with section('Prediction'):
        # auto select best result
        if model_id is None:
            sort_key = Utils.get_appropriate_dataset(project.cv_method, project.validation_type,
                                                     project.validation_params)
            model = project.search_models(sort_key=sort_key)[0]
            model_id = model.id

        predictions = project.predict(model_id=model_id, dataset_id=dataset.id)

        if config.get_param(cmd, param='feature_impact') or config.get_param(cmd, param='reasoncode'):
            feature_impacts = project.get_feature_impact(model_id)
            feature_impacts = pd.DataFrame(feature_impacts)
            # feature_impacts.to_csv(f"feature_impact_{model_id}.csv", index=False)

        if config.get_param(cmd, 'reasoncode'):
            max_codes = config.get_param(cmd, param='max_codes') or 3

            rc_job = project.get_reasoncode_job(model_id, dataset.id, max_codes=max_codes)

            # TODO: parameterize in config
            time_to_wait_for_reasoncode = 20*60 # sec
            reasoncode = rc_job.get_result_when_complete(time_to_wait_for_reasoncode)
            reasoncodes = pd.DataFrame(reasoncode.get_all_as_dataframe())
            reasoncodes.drop(columns=[prediction_column], inplace=True)
            predictions = pd.merge(left=predictions, right=reasoncodes, on='row_id')

    if config.get_param(cmd, param='merge_origin'):
        predictions = merge_dataset(predictions, input_df)

    with section('Output result'):
        IOManager(io_type='output', io_params=config.get_param(cmd, param='output')).output(predictions)

    with section('clearning'):
        if config.get_param(cmd, param='del_dataset') is not False:
            project.delete_dataset(dataset.id)


def merge_dataset(predictions, input_df):
    with section('Merge dataset with prediction'):
        merged = pd.merge(left=input_df, right=predictions, left_index=True, right_on='row_id')
        merged.drop(columns=['row_id'], inplace=True)

        return merged


# utility commands

@cli.command(help='fetch project details')
@click.pass_context
@share_option
def get_projects(ctx, credential):  # shared options
    max_len = [32, 24, 10, 20, 16]
    projects = dr.Project.list()
    columns = [
        'name',
        'project_id',
        'stage',
        'description',
        'partition',
    ]

    data = []
    for project in projects:
        status = project.get_status()
        partition = project.partition
        partitioning = "None"
        if partition != {}:
            if 'cv_method' not in partition:
                cv_method = 'random'
            else:
                cv_method = partition['cv_method']
            partitioning = cv_method
            partitioning += f": {partition['validation_type']}"

        values = [project.project_name, project.id, status['stage'], status['stage_description'], partitioning]
        data.append(values)
    Utils.prettyprint_table(columns, data, max_len)


@cli.command(help='dump the project environment settings as yaml.')
@click.pass_context
@share_option
@click.argument('project_id', nargs=1, metavar='<project_id>')
def get_project_setting(
        ctx,
        credential,  # shared options
        project_id):

    project = Project(project_id=project_id)

    setting = yaml.load(project.to_yml())
    setting = {'environment' : setting}
    click.echo(pyaml.dump(setting))


@cli.command(help='fetch the project detail')
@click.pass_context
@share_option
@click.argument('project_id', nargs=1, metavar='<project_id>')
@click.option('--verbose', '-v', is_flag=True)
def get_project(
        ctx,
        credential,  # shared options
        project_id,
        verbose):
    # FIXME: awful
    project = Project(project_id=project_id)
    metric = project.metric

    click.echo("### params")
    for k, v in yaml.load(project.to_yml()).items():
        click.echo(f"{k} : {v}")

    click.echo("\n### feature list")
    for featurelist in project.dr_project.get_featurelists():
        click.echo(f"* {featurelist.name}")
        if verbose:
            data = []
            for feature, attr in project.get_features(featurelist.name).items():
                d = [feature]
                for k, v in attr.items():
                    d.append(v)
                data.append(d)
            else:
                columns = ['name'] + list(attr.keys())
            Utils.prettyprint_table(columns, data, [24])
        click.echo()

    click.echo(f"### top 10 models with {project.metric}")
    sort_key = Utils.get_appropriate_dataset(project.cv_method, project.validation_type, project.validation_params)

    models = project.search_models(featurelist_name=None, sort_key=sort_key)[:10]
    data = [(model.model_type, model.id, model.is_frozen, model.metrics[project.metric][sort_key],
             model.featurelist_name) for model in models]

    columns = ['type', 'id', 'is_frozen', f"{sort_key}", 'featurelist_name']
    Utils.prettyprint_table(columns, data, max_len=[16, 24, 9, 16, 16])

    click.echo()
    if verbose:
        click.echo(f"### frozen models")
        models = project.search_models(featurelist_name=None, is_frozen=True, sort_key=sort_key)
        data = [(model.model_type, model.id, model.is_frozen, model.metrics[project.metric][sort_key])
                for model in models]

        columns = ['type', 'id', 'is_frozen', f"{sort_key} : {project.metric}"]
        Utils.prettyprint_table(columns, data, max_len=[16, 24, 9, 24])

@cli.command(help='validate configuration file')
@click.argument('config_path', nargs=1, type=click.Path(exists=True), metavar='</path/to/configuration-file>')
@click.pass_context
@share_config
def validate(ctx, config_path):
    config = ctx.obj['config']
    if config.is_valid():
        print(f"{config.file_path} is valid")

@cli.command(help='download and install boston housing and iris dataset')
@click.option('--path', type=click.Path(), default='./data/raw')
def create_dataset(path):
    Utils.create_dataset(path)


# thx orisano
@contextlib.contextmanager
def section(name):
    start = time.time()
    click.echo("start    '{}'".format(name))
    yield
    click.echo("finished '{}'".format(name))
    click.echo(f"...elapsed time: {time.time()-start: 0.3f} s\n")

def main():
    cli(obj={})

if __name__ == '__main__':
    main()
