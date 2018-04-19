from drctrl.lib.Exceptions import NotSufficientParams, NotSpecifiedValidParam
from drctrl.lib.Utils import get_currenttime_string
from drctrl.lib.Utils import string_to_datetime
from drctrl.lib.Utils import DateTimePartitionParams
from drctrl.lib.Utils import get_logger
import datarobot as dr
from datarobot.helpers.partitioning_methods import get_class
from copy import deepcopy
import pyaml

MODE = {
    'fullauto': dr.AUTOPILOT_MODE.FULL_AUTO,
    'manual': dr.AUTOPILOT_MODE.MANUAL,
    'quick': dr.AUTOPILOT_MODE.QUICK,
    'semi': dr.AUTOPILOT_MODE.SEMI_AUTO,
}

logger = get_logger(__file__)

# if project_id is None, then new project is provided
# autopilot: FULLAUTO, MANUAL, QUICK ref) https://datarobot-public-api-client.readthedocs-hosted.com/en/v2.8.0/entities/project.html?highlight=get_metrics#start-modeling
#


class Project:
    def __init__(
            self,
            project_id=None,
            dataset= None,
            project_name=None,
            metric=None,
            target_feature=None,
            autopilot='manual',
            cv_method='random',
            validation_type='TVH',
            # partitioning params
            validation_params={'holdout_pct': 20,
                               'validation_pct': 10},
            convert_features=None,
            **kwargs):

        self.project_id = project_id
        self.dataset = dataset
        self.project_name = project_name
        self.metric = metric
        self.target_feature = target_feature
        self.autopilot = MODE[autopilot]
        self.cv_method = cv_method
        self.validation_type = validation_type
        self.validation_params = validation_params
        self.convert_features = convert_features

        if project_id is not None:
            # already exist
            # TODO: exception handling
            self.dr_project = dr.Project.get(project_id)
            self.project_name = self.dr_project.project_name
            self.metric = self.dr_project.metric
            self.target_feature = self.dr_project.target
            partition = self.dr_project.partition

            if partition != {}:
                if 'cv_method' not in partition:
                    self.cv_method = 'random'
                else:
                    self.cv_method = partition['cv_method']

                self.validation_type = partition['validation_type']
                partition.pop('cv_method')
                partition.pop('validation_type')
            else:
                self.cv_method = None
                self.validation_type = None

            if self.cv_method == 'datetime':
                self.validation_params = DateTimePartitionParams.to_dict(self.project_id)
            else:
                self.validation_params = partition

            # convert requested format
            if self.convert_features is not None:
                exists_features = [feature.name for feature in self.dr_project.get_features()]

                for req in self.convert_features:
                    if req['rename_to'] in exists_features:
                        continue
                    self.convert_feature(**req)

    # return new project instance
    def build_project(self, dataframe):
        self.dr_project = dr.Project.create(dataframe, project_name=self.project_name)
        self.project_id = self.dr_project.id

        # set partitioning and metrics
        if self.metric is not None and self.target_feature is not None:
            self.set_target_and_run_autopilot(self.target_feature, self.metric)

        # convert requested format
        if self.convert_features is not None:
            exists_features = [feature.name for feature in self.dr_project.get_features()]

            for req in self.convert_features:
                if req['rename_to'] in exists_features:
                    continue
                self.convert_feature(**req)

        return self.project_id

    def set_target_and_run_autopilot(self, target_feature, metric):
        metrics_list = self.dr_project.get_metrics(feature_name=target_feature)['available_metrics']
        if metric not in metrics_list:
            raise NotSpecifiedValidParam(f"metric should be specified from {metrics_list}")

        spec = self.get_partition_spec(method=self.cv_method, _type=self.validation_type, params=self.validation_params)

        self.dr_project.set_target(target=target_feature, metric=metric, mode=self.autopilot, partitioning_method=spec)

        return True

    def set_name(self, name):
        self.dr_project.rename(name)

    def get_partition_spec(self, method, _type, params):
        if method == 'datetime':
            spec = DateTimePartitionParams.from_dict(params)
        else:
            spec = get_class(method, _type)(**params)
        return spec

    def get_featurelist_by_name(self, featurelist_name):
        featurelists = self.dr_project.get_featurelists()
        for featurelist in featurelists:
            if featurelist_name == featurelist.name:
                return featurelist
        else:
            return None

    # create new feature
    def create_featurelist(self, featurelist_name=None, source_featurelist='Raw Features', except_features=None):
        if except_features is None:
            except_features = []

        featurelist = self.get_featurelist_by_name(source_featurelist)

        # if specified feature does not exist, warning user
        target_features = list(set(featurelist.features) - set(except_features))
        for feature in (set(except_features) - set(featurelist.features)):
            logger.warning(f"{feature} is specified, but not in {source_featurelist}")

        new_featurelist = self.dr_project.create_featurelist(featurelist_name, target_features)

        return new_featurelist.id

    def run_autopilot(self, featurelist_id, autopilot_mode):
        # True or Error?
        return self.dr_project.start_autopilot(featurelist_id, mode=MODE[autopilot_mode])

    def get_fit_job(self, model_id=None, sample_pct=None, featurelist_id=None, autopilot='fullauto', **kwargs):

        if model_id is None:
            # autopilot mode
            logger.debug(f"run autopilot as {autopilot} mode with {featurelist_id}")
            self.run_autopilot(featurelist_id, autopilot_mode=autopilot)
            model_job = None
        else:
            model = dr.Model.get(self.dr_project.id, model_id)
            model_job_id = model.train(sample_pct, featurelist_id)
            model_job = dr.ModelJob.get(project_id=self.dr_project.id, model_job_id=model_job_id)

        return model_job

    def fit(self,
            model_id=None,
            sample_pct=None,
            featurelist_name=None,
            source_featurelist='Raw Features',
            except_features=None,
            autopilot='fullauto',
            wait_for_completion=True,
            **kwargs):
        if self.get_featurelist_by_name(featurelist_name) is not None:
            featurelist_name = None

        if featurelist_name is None:
            featurelist_name = get_currenttime_string()

        featurelist_id = self.create_featurelist(featurelist_name, source_featurelist, except_features)

        model_job = self.get_fit_job(
            model_id=model_id, sample_pct=sample_pct, featurelist_id=featurelist_id, autopilot=autopilot)

        model_type = 'autopilot' if model_job is None else model_job.model_type
        if wait_for_completion:
            logger.debug(f"wait for fitting completion")
            if model_job is None:
                # never timeout
                self.dr_project.wait_for_autopilot()
            else:
                model_job.wait_for_completion()

        return featurelist_name, model_type

    def get_frozen_datetime_job(self,
                                model_id,
                                row_count=None,
                                duration=None,
                                start_date=None,
                                end_date=None,
                                time_window_sample_pct=None,
                                **kwargs):
        if row_count is None and duration is None:
            if start_date is None or end_date is None:
                raise NotSufficientParams

        if start_date is not None:
            start_date = string_to_datetime(start_date)
            end_date = string_to_datetime(end_date)

        model = dr.Model.get(project=self.project_id, model_id=model_id)

        model_job = model.request_frozen_datetime_model(
            training_row_count=row_count,
            training_duration=duration,
            training_start_date=start_date,
            training_end_date=end_date)
            # maybe this param is enable from v2.8~
            #time_window_sample_pct=time_window_sample_pct)

        return model_job

    def get_frozen_job(self, model_id, sample_pct=None, **kwargs):
        model = dr.Model.get(project=self.project_id, model_id=model_id)

        model_job = model.request_frozen_model(sample_pct=sample_pct)

        return model_job

    def frozen(self, model_id, **params):
        if self.cv_method == 'datetime':
            frozen_method = self.get_frozen_datetime_job
        else:
            frozen_method = self.get_frozen_job

        model_job = frozen_method(model_id, **params)
        model_job.wait_for_completion()
        model = model_job.get_model(self.project_id, model_job.id)

        return model.id

    def upload_dataset(self, dataframe=None):
        dataset = self.dr_project.upload_dataset(dataframe)
        return dataset
    
    def delete_dataset(self, dataset_id):
        dataset = dr.models.PredictionDataset.get(self.project_id, dataset_id)
        return dataset.delete()

    def convert_feature(self, name, rename_to=None, variable_type=None):
        if rename_to is None:
            rename_to = name + '_' + variable_type.lower()

        feature = self.dr_project.create_type_transform_feature(
            name=rename_to, parent_name=name, variable_type=variable_type)

        return feature

    def get_prediction_job(self, model_id=None, dataset_id=None, **kwargs):
        model = dr.Model.get(project=self.project_id, model_id=model_id)
        predict_job = model.request_predictions(dataset_id)

        return predict_job

    def predict(self, model_id=None, dataset_id=None, wait_to_prediction_time=60*20, **kwargs):
        prediction_job = self.get_prediction_job(model_id, dataset_id)
        predictions = prediction_job.get_result_when_complete(wait_to_prediction_time)

        return predictions

    # time_to_wait_for_impact : float, sec
    def get_feature_impact(self, model_id, time_to_wait_for_impact=60*60):
        model = dr.Model.get(project=self.project_id, model_id=model_id)

        try:
            feature_impacts = feature_impacts = model.get_feature_impact()  # if they've already been computed
        except dr.errors.ClientError as e:
            assert e.status_code == 404  # the feature impact score haven't been computed yet
            impact_job = self.get_feature_impact_job(model_id)
            feature_impacts = impact_job.get_result_when_complete(time_to_wait_for_impact)

        return feature_impacts

    def search_models(self, featurelist_name=None, is_frozen=False, sort_key='validation'):
        def f_key(model, sort_key, desc):
            is_None = model.metrics[self.metric][sort_key] is None
            result = model.metrics[self.metric][sort_key]

            return (is_None ^ desc, result)

        models = self.dr_project.get_models()

        target_models = []
        for model in models:
            if featurelist_name is not None and model.featurelist_name != featurelist_name:
                continue
            if model.is_frozen != is_frozen:
                continue
            target_models.append(model)

        desc = False if self.dr_project.target_type == 'Regression' else True
        _sorted = sorted(target_models, key=lambda model: f_key(model, sort_key, desc), reverse=desc)

        return _sorted

    def get_feature_impact_job(self, model_id):
        model = dr.Model.get(project=self.project_id, model_id=model_id)
        impact_job = model.request_feature_impact()

        return impact_job

    def get_reasoncode_job(self, model_id, dataset_id, max_codes=None):
        # Initialize reason codes
        rci_job = dr.ReasonCodesInitialization.create(self.project_id, model_id)
        rci_job.wait_for_completion()

        # Compute reason codes with default parameters
        job_id = dr.ReasonCodes.create(self.project_id, model_id, dataset_id, max_codes=max_codes)

        return job_id

    def get_features(self, featurelist_name):
        featurelists = self.dr_project.get_featurelists()
        featurelists = {featurelist.name: featurelist.features for featurelist in featurelists}
        featurelist = featurelists[featurelist_name]

        features = self.dr_project.get_features()
        feature_column = ['type', 'importance']
        feature_dict = dict()

        for feature in features:
            feature_dict[feature.name] = {'type': feature.feature_type, 'importance': feature.importance}

        ret = dict()
        for feature in featurelist:
            ret[feature] = feature_dict[feature]

        return ret

    # get frozened model whose parent is model_id
    def get_frozen_models(self, model_id):
        models = self.search_models(is_frozen=True)
        ret = []
        for model in models:
            frozen_model = dr.models.FrozenModel.get(self.project_id, model.id)
            if frozen_model.parent_model_id == model_id:
                ret.append(frozen_model)

        return ret

    def to_yml(self):
        params = deepcopy(self.__dict__)
        params.pop('dr_project')
        return pyaml.dump(params)
