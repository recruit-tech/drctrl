## I/O plugins

You can specify various input/output type e.g. file, redshift, bigquery, url.

### file

file input/output option

```yaml
type: file
path: <file path>
filename: <file name>
```

### url

url input option

```yaml
type: url
url: https://path/to/dataset
```

#### options

* `type`
   * type: str
   * required: True
* `url`
   * http or https url
   * type: str
   * required: True

### redshift

redshift input/output option.


```yaml
type: redshift
aws_key_id: <aws_key_id>
aws_secret_key: <aws_secret_access_key>
bucket: <bucket name>
key_path: <key path>
host: <hostname>
port: <port>
user: <user name>
password: <password>
dbname: <database name>
schema: <schema name>
table: <table name>
```

#### options

* `aws_key_id`
   * type: str
   * required: True
* `aws_secret_key`
   * type: str
   * required: True
* `bucket`
   * type: str
   * required: True
* `key_path`
   * type: str
   * required: True
* `host`
   * type: str
   * required: True
* `port`
   * type: str
   * required: True
* `user`
   * type: str
   * required: True
* `password`
   * type: str
   * required: True
* `dbname`
   * type: str
   * required: True
* `schema`
   * type: str
   * required: True
* `table`
   * type: str
   * required: True
