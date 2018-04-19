## drctrl

drctrl is a tool for automatically configuration for Datarobot. drctrl can manage features provided datarobot like building project, training, freezing, prediction.

python support:	3.6.x and greater

## 1. Insallation

```bash
$ pip install drctrl
```

## 2. Get started

Setting up credential

```bash
$ cat << _EOF_ > ~/.config/datarobot/drconfig.yaml
token: <datarobot-user-token>
endpoint: <datarobot-api-endpoint>
_EOF_

# get all projects
$ drctrl get_projects

# get project detail
$ drctrl get_project <project_id>

# you can get the exist project configuration for drctrl with
$ drctrl get_project_setting <project_id>
```

### Build a new project

Download Boston Housing dataset in UCI [url](https://archive.ics.uci.edu/ml/machine-learning-databases/housing/Index).

```bash
# downloading datase into `./data/raw/`
$ drctrl create_dataset
```

Setting up configure.yml

```yaml
environment:
   project_id: # if null, build a new project
   project_name: 'sample_project'
   target_feature: target
   metric: 'RMSE' 
   cv_method: 'random'
   validation_type: 'CV' 
   validation_params:
      holdout_pct: 20
      #validation_pct: 10
      reps: 3    # number of cross validation folds to use
      seed: 2017 # a seed to use for randomization
   dataset:
       type: file
       path: './data/raw'
       filename: 'boston.csv'
   autopilot: 'manual' # fullauto, quick, manual
   convert_features:
      - {name: RAD, rename_to: RAD_categoricalInt, variable_type: categoricalInt}

fit:
   model_id:  # if None, run autopilot
   autopilot: 'fullauto'
   featurelist_name: 'without_feature'  # if already exist, current time string will be used
   source_featurelist: 'Raw Features'
   except_features:
      - 'NOX'
      
predict:
   model_id:  # if None, a model will be automatically selected 
   input:     # prediction target dataset
       type: 'file'
       path: './data/raw/'
       filename: 'boston.csv'
   reasoncode: True
   merge_origin: True 
   feature_impact: True
   output:   # output format
       type: 'file'
       path: './'
       filename: 'prediction.csv'
```

Run Drctrl with configuration

```bash
$ drctrl apply configure.yml
```

Details of commands and options is [here](docs/options.md)

## 3. Commands

```bash
Usage: drctrl [OPTIONS] COMMAND [ARGS]...

Options:
  --credential PATH
  --help             Show this message and exit.

Commands:
  apply                  Apply all commands in configuration file
  build                  building project on the basis of a configuration file
  create_dataset         download and install boston housing and iris dataset
  fit                    training model on the basis of a configuration file
  frozen                 freezing model on the basis of configuration file
  get_project            fetch the project detail
  get_project_setting    dump the project parameter as yaml file
  get_projects           fetch project details
  predict                predicting on the basis of a configuration file
  validate               validate configuration file
```


## 4. I/O format

There are several options for I/O format. redshift, file, url format can be specified as `dataset` param in `environment`, `input` / `output` param in `predict` for now.

Details are [here](docs/iotype.md)

### file format

```yaml
environment:
   dataset:
      type: file
      path: /path/to/dataset
      filename: dataset.csv
```

or 

```yaml
predict:
   input:
      type: redshift
      aws_key_id: <aws_access_key_id>
      aws_secret_key: <aws_secret_access_key>
      bucket: <s3_bucket>
      key_path: <s3_key>
      dbname: <redshift_dbname>
      host: <redshift_host>
      port: <redshift_port>
      user: <redshift_user>
      password: <redshift_password>
      schema: <target_table_schema>
      table:  <target_table_name>
   output:
      type: redshift
      aws_key_id: <aws_access_key_id>
      aws_secret_key: <aws_secret_access_key>
      bucket: <s3_bucket>
      key_path: <s3_key>
      dbname: <redshift_dbname>
      host: <redshift_host>
      port: <redshift_port>
      user: <redshift_user>
      password: <redshift_password>
      schema: <target_table_schema>
      table:  <target_table_name>
```

and so on.

## 5. template

drctrl support [Jinja2](https://github.com/pallets/jinja/tree/master/jinja2) template format. Configuration file have to satisfy file extention format `.yml.tmple` .

In tmpl file, `env['FILE_PATH']` variable is replaced by environment variable `FILE_PATH`.
The following is an example.

```yaml
environment:
    project_id: {{ env.PROJECT_ID }}

predict:
    model_id: {{ env.MODEL_ID }}
    dataset:
      type: file
      path: {{ env['DATASET_PATH'] }}
      filename: {{ env['DATASET_FILE'] }}
    feature_impact: false
    reasoncode: false
    merge_origin: true
```
