from sklearn import datasets
import datarobot as dr
import pandas as pd
import numpy as np
import contextlib
import requests
import os
import sys
from copy import deepcopy
import yaml
from datetime import datetime
import logging

# const

time_format = '%Y%m%d_%H%M%S'

# methods


def get_currenttime_string():
    now = datetime.now()
    return datetime_to_string(now)


def datetime_to_string(dt):
    return dt.strftime(time_format)


def string_to_datetime(str_dt):
    if type(str_dt) is not str:
        str_dt = str(str_dt)
    return datetime.strptime(str_dt, time_format)


# select appropriate dataset to get best model by cv_method and validation_type
def get_appropriate_dataset(cv_method, validation_type, validation_params):
    dataset = 'validation'

    if cv_method == 'datetime':
        if len(validation_params['backtests']) > 1:
            dataset = 'crossValidation'
    elif validation_type == 'CV':
        dataset = 'crossValidation'

    return dataset


# select appropriate column in predictions whether target type is regression
#self.dr_project.target_type
def get_appropriate_prediction_column(target_type):
    ret = 'prediction'

    if target_type == 'classification':
        ret = 'positive_probability'

    return ret

def create_dataset(path='./data/raw'):
    # regression
    boston = datasets.load_boston()
    _boston = np.concatenate([boston.data, boston.target[:, None]], axis=1)
    boston_df = pd.DataFrame(_boston, columns=list(boston.feature_names) + ['target'])

    # classification
    iris = datasets.load_iris()
    _iris = np.concatenate([iris.data, iris.target[:, None]], axis=1)
    iris_df = pd.DataFrame(_iris, columns=list(iris.feature_names) + ['target'])

    try:
        os.makedirs(path)
    except FileExistsError:
        pass

    boston_df.to_csv(f"{path}/boston.csv", index=False)
    iris_df.to_csv(f"{path}/iris.csv", index=False)


def prettyprint_table(columns, data, max_len=[]):
    def _format(row, lengths):
        ret = []
        for r, length in zip(map(str, row), lengths):
            fixed = r[:length]
            ret += [f"{fixed:{length}s}"]
        return ret

    if max_len == []:
        max_len = [16] * len(columns)
    else:
        if len(max_len) < len(columns):
            max_len += [16] * (len(columns) - len(max_len))

    # print header
    print('\t'.join(_format(columns, max_len)))
    delimiter = '-'
    delimiters = [delimiter * length for length in max_len]
    print('\t'.join(_format(delimiters, max_len)))

    for row in data:
        print('\t'.join(_format(row, max_len)))


datetime_specification_attributes = [
    'datetime_partition_column',
    'autopilot_data_selection_method',
    'validation_duration',
    'holdout_start_date',
    'holdout_duration',
    'disable_holdout',
    'gap_duration',
    'number_of_backtests',
    'backtests',
    'use_time_series',
    'default_to_a_priori',
    'feature_derivation_window_start',
    'feature_derivation_window_end',
    'forecast_window_start',
    'forecast_window_end',
]

class DateTimePartitionParams:
    def __init__(self, **kwargs):
        # backtests
        pass

    @staticmethod
    def get_params(project_id):
        instance = dr.DatetimePartitioning.get(project_id)
        ret = dict()
        for a in datetime_specification_attributes:
            try:
                ret[a] = instance.__getattribute__(a)
            except AttributeError:
                pass

        return ret

    @staticmethod
    def to_dict(project_id):
        return DateTimePartitionParams._parse_params(DateTimePartitionParams.get_params(project_id))

    @staticmethod
    def _parse_params(params):
        ret = deepcopy(params)
        # split into index, gap_duration, validation_start_date, validation_duration
        ret['backtests'] = []
        for backtest in params['backtests']:
            d = dict()
            d['index'] = backtest.index
            d['gap_duration'] = backtest.gap_duration
            d['validation_duration'] = backtest.validation_duration
            d['validation_start_date'] = datetime_to_string(backtest.validation_start_date)
            ret['backtests'].append(d)
        ret['holdout_start_date'] = datetime_to_string(ret['holdout_start_date'])

        return ret

    @staticmethod
    def to_yml(project_id):
        params = DateTimePartitionParams.get_params(project_id)
        return yaml.dump(DateTimePartitionParams._parse_params(params))

    @staticmethod
    def from_dict(_params):
        params = deepcopy(_params)
        if len(params['backtests']) > 0:
            backtests = []
            for backtest in params['backtests']:
                backtest['validation_start_date'] = string_to_datetime(backtest['validation_start_date'])
                backtests.append(dr.BacktestSpecification(**backtest))
            params['backtests'] = backtests
        params['holdout_start_date'] = string_to_datetime(params['holdout_start_date'])
        return dr.DatetimePartitioningSpecification(**params)


# http://masnun.com/2016/09/18/python-using-the-requests-module-to-download-large-files-efficiently.html
def fetch_file(source_url, dest_path):
    res = requests.get(source_url, stream=True)

    parsed = requests.compat.urlparse(res.url)
    filename = parsed.path.split('/')[-1]
    dest_path = f"{os.path.abspath(dest_path)}/{filename}"

    handle = open(dest_path, "wb")
    for chunk in res.iter_content(chunk_size=512):
        if chunk:  # filter out keep-alive new chunks
            handle.write(chunk)

    return filename

# https://stackoverflow.com/questions/42952623/stop-python-module-from-printing
def suppressStdOutput(func):
    def wrapper(*args, **kwargs):
        with open(os.devnull,"w") as devNull:
            original = sys.stdout
            sys.stdout = devNull
            func(*args, **kwargs)
            sys.stdout = original
    return wrapper

def suppressStdError(func):
    def wrapper(*args, **kwargs):
        with open(os.devnull,"w") as devNull:
            original = sys.stderr
            sys.stderr = devNull
            func(*args, **kwargs)
            sys.stderr = original
    return wrapper


def get_logger(log_name):
    _logger = logging.getLogger(log_name)

    if not _logger.hasHandlers():
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        _logger.addHandler(handler)
        _logger.setLevel(logging.INFO)

    return _logger
