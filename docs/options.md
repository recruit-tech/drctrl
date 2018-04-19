## Description

drctrl can operate some datarobot features (project building, training, prediction, freezing model) by specifying configuration file.

Each commands must be specified in top-level field of yaml configuration file.

```
environment:
   options:

fit:
   options:

frozen:
   oprions:

predict:
   options:
```



### environment

* project setting field
* if project is not supplied, automaticaly create a new project based on given options

#### basic usage

create a new project

```yaml
environment:
   project_id: 
   project_name: 'sample project'
   target_feature: target
   metric: AUC
   cv_method: 'random'
   validation_type: 'CV'
   validation_params: 
      holdout_pct: 20
      reps: 3
      seed: 2017
   dataset:
       type: file
       path: ./data/raw/
       filename: boston.csv
   autopilot: 'manual' 
```

When project is given, other options are not required.

```yaml
environment:
  project_id: <project_id>
```

#### options

* `project_id`
   * if null is specified, automaticaly create a new project based on given options
   * type: str or none
   * required: False
* `project_name`
   * type: str
   * required: False
* `target_feature`
   * target feature name
   * type: str
   * required: True
* `metric`
   * optimization metric
      * valid metrics depends on project type (classification, regression)
      * see [datarobot api metrics](https://datarobot-public-api-client.readthedocs-hosted.com/en/v2.8.1/entities/project.html?highlight=metrics)
   * type: str
   * required: True
* `cv_method`
   * partitioning method (it is prefix of datarobot partitioning class name)
      * `datetime`, `user`, `straitified`, `random`, `user`, `group`
      * see [data robot api doc](https://datarobot-public-api-client.readthedocs-hosted.com/en/v2.8.1/api/partitions.html)
   * type: str
   * required: True
* `validation_type`
   * partition type
      * `CV` : cross validation
      * `TVH` : train, validation holdoutset
   * type: str
   * required: True
* `validation_params`
   * this option depends on `cv_method` and `validation_type`
     * required options can be confirmed at [data robot api doc](https://datarobot-public-api-client.readthedocs-hosted.com/en/v2.8.1/api/partitions.html)
     * practically, you should try making a copy of partition settings from already exist project by using `drctrl get_partition_setting` option.
   * type: map
   * required: True
   * allowempty: True
* dataset
   * dataset option
      * see [io plugins](./iotype.md)
   * type: map
   * required: True
   * allowempty: True
* `autopilot`
   * run autopilot when creating project
      * `fullauto`
      * `manual`
   * type: str
   * required: True
* `convert_features`
   * convert feature type
      * give following format

      ```yaml
      cconvert_features:
        - {name: <source_feature_name>, rename_to: <dest_name>, variable_type: <type>}
        - {name: <source_feature_name>, rename_to: <dest_name>, variable_type: <type>}
        - {name: <source_feature_name>, rename_to: <dest_name>, variable_type: <type>}
      ```

   * type: sequence
   * required: False

### fit

#### basic usage

```yaml
fit:
   model_id: <model_id> or none
   source_featurelist: 'Raw Features'
```

#### options

* `model_id`
   * if model_id is null, autopilot is executed.
   * type: str or none
   * required: True
* `sample_pct`
   * the percentage of the project dataset used in training the model
   * type: float
   * required: False
* `autopilot`
   * if model_id is not specified, this option is required.
   * type: str
   * required: False
* `featurelist_name`
   * featurelist name
   * type: str
   * required: False
* `source_featurelist`
   * type: str
   * required: True
* `except_features`
   * create featurelist without specified features
   * required: False
   * type: sequence

   ```yaml
      except_features:
        - 'feature_2'
        - 'feature_1'
   ```

* `wait_for_completion`
   * wait for model creation or autopilot completion.
   * type: bool
   * required: False

### frozen

#### basic usage

```yaml
frozen:
   model_id: <model_id>
   sample_pct: 50.0
```

#### options

* `model_id`
   * if None, target model is automaticaly selected based on the order of validation
   * type: str or null
   * required: True
* `sample_pct`
   * the percentage of the project dataset used in training the model
   * type: float
   * required: False
* `training_row_count`
   * only required for models in datetime partitioned projects. If specified, defines the number of rows used to train the model and evaluate backtest scores.
   * type: int
   * required: False
* `training_duration`
   * only required for models in datetime partitioned projects. a duration string specifying the duration spanned by the data used to train the model and evaluate backtest scores.
   * type: int
   * required: False
* `start_date`
   * only required for models in datetime partitioned projects. 
   * format: `yyyymmdd_hhmmss`
   * type: str
   * required: False
* `end_date`
   * only required for models in datetime partitioned projects. 
   * format: `yyyymmdd_hhmmss`
   * type: str
   * required: False

### predict

#### basic usage

```yaml
predict:
   model_id: <model_id> or null
   input:
       type: file
       path: './data/raw/'
       filename: boston.csv
   output:
       type: file
       path: './'
       filename: result.csv
```

#### options

* `model_id`
   * if None, target model is automaticaly selected based on the order of validation
   * type: str or null
   * required: True
* `del_dataset`
   * delete dataset when prediction is completed
   * type: bool
   * required: False
* `reasoncode`
   * if True, reasoncode will be calculated with the model.
   * type: bool
   * required: False
* `max_codes`
   * only required for calculating reasoncode. 1-10 can be specified.
   * type: int
   * required: False
* `merge_origin`
   * if True, prediction result is merged with given dataset specified in `input` field.
   * type: bool
   * required: False
* `feature_impact`
   * if True, feature impact will be calculated.
      * when `reasoncode` is specified, this option will be specified.
   * type: bool
   * required: False
* `input`
   * input dataset option
      * see [io plugins](./iotype.md)
   * type: map
   * allowempty: True
   * required: True
   * options(map):
      * `type`
         * input type
         * type: str
         * required: True
* `output`
   * output dataset option
      * see [io plugins](./iotype.md)
   * type: map
   * allowempty: True
   * required: True
   * options(map):
      * `type`
         * input type
         * type: str
         * required: True
