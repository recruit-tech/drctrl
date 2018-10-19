import os
from sqlalchemy import create_engine
from sqlalchemy.types import VARCHAR
from pandas.io.sql import SQLTable, pandasSQL_builder
import tempfile
import numpy as np
import boto3
import json
import pandas as pd
from sqlalchemy import text
from datetime import datetime
import csv

# https://github.com/bufferapp/rsdf

def get_buffer_data_url(s3_access_key, s3_secret_key, s3_bucket, **kwargs):
    return 's3://{s3_access_key}:{s3_secret_key}@{s3_bucket}'.format(**locals())


def get_dataframe_column_object_types(dataframe):
    df_grouped_types = dataframe.columns.to_series().groupby(dataframe.dtypes).groups
    object_types = df_grouped_types.get(np.dtype('O'))
    object_types = object_types if object_types is not None and object_types.any() else []

    return object_types


def create_copy_statement(tablename, schemaname, columns, s3_bucket_url, credentials):
    if schemaname == "" or schemaname is None:
        full_table_name = tablename
    else:
        full_table_name = "{schemaname}.{tablename}".format(**locals())

    stmt = ("copy {full_table_name} {columns} from '{s3_bucket_url}' "
            "credentials '{credentials}' "
            "EMPTYASNULL "
            "BZIP2 "
            "removequotes "
            "ESCAPE "
            "DELIMITER ',';".format(**locals()))
    return stmt

def prepare_dataframe_for_schema(dataframe):
    dataframe = dataframe.copy(deep=True)
    object_types = get_dataframe_column_object_types(dataframe)
    for c in object_types:
        dataframe[c] = dataframe[c].fillna('')

    return dataframe


def prepare_dataframe_for_loading(dataframe):
    # do some cleanup
    #   - escape newlines
    #   - convert all dicts and lists to json formatted strings
    dataframe = dataframe.copy(deep=True)
    object_types = get_dataframe_column_object_types(dataframe)
    for c in object_types:
        dataframe[c] = dataframe[c].fillna('')
        dataframe[c] = dataframe[c].map(lambda o: o.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] if isinstance(o, datetime) else o)
        dataframe[c] = dataframe[c].map(lambda o: json.dumps(o) if not isinstance(o, str) else o)
        #dataframe[c] = dataframe[c].map(lambda s: s.encode('unicode-escape').decode() if isinstance(s, str) else s)
    return dataframe



class rsdf:
    def __init__(self, user, password, dbname, host, port=5439):
        self.user = user
        self.password = password
        self.dbname = dbname
        self.host = host
        self.port = port

        self.engine = self._get_engine()

    def _get_engine(self):
        engine_string = "postgresql+psycopg2://{}:{}@{}:{}/{}".format(
                self.user, self.password, self.host, self.port, self.dbname)

        return create_engine(engine_string)

    def query_to_df(self, query):
        df = pd.read_sql_query(query, self.engine)

        return df


    def get_table_ddl(self, table_name, schema='public'):
        query = text("""
            select ddl
                from(
                    select *
                    from admin.v_generate_tbl_ddl
                    where schemaname = :schema and tablename= :table
                )
                order by seq
        """)
        r = self.engine.execute(query, table=table_name, schema=schema)
        lines = [row[0] for row in r]
        return ('\n'.join(lines))



    def _get_sa_table_for_dataframe(self, dataframe, tablename, schemaname):
        # get max lengths for strings and use it to set dtypes
        dtypes = {}
        object_types = get_dataframe_column_object_types(dataframe)

        for c in object_types:
            if dataframe[c].dtype == np.dtype('O'):
                n = dataframe[c].map(lambda c: len(str(c)) if c else None).max()
                if np.isnan(n):
                    n = 0

                # we use 10 times the max length or varchar(max)
                dtypes[c] = VARCHAR(min([(n+1)*16, 65535]))

        table = SQLTable(tablename, pandasSQL_builder(self.engine, schema=schemaname),
                         dataframe, if_exists=True, index=False, dtype=dtypes)

        return table

    def execute(self, query):
        return self.engine.execute(query)


    def load_dataframe(self, dataframe, tablename, schemaname='public', columns=None, exists='fail',
            aws_access_key_id=None, aws_secret_access_key=None, s3_bucket=None):
        table = self._get_sa_table_for_dataframe(prepare_dataframe_for_schema(dataframe), tablename, schemaname)

        dataframe = prepare_dataframe_for_loading(dataframe)
        s3_url = 'tmp/{0}.csv.bz2'.format(tablename)
        

        # first compress locally and then stream to s3
        tfile = tempfile.NamedTemporaryFile(suffix='.bz2')
        dataframe.to_csv(tfile.name, header=False, index=False, sep=',',
                compression='bz2', na_rep='', quoting=csv.QUOTE_NONNUMERIC)

        s3client = boto3.client('s3')
        s3client.upload_fileobj(tfile, s3_bucket, s3_url)

        if columns is None:
            columns = ''
        else:
            columns = '()'.format(','.join(columns))
        credentials = 'aws_access_key_id={aws_access_key_id};aws_secret_access_key={aws_secret_access_key}'.format(**locals())

        s3_bucket_url = f"s3://{s3_bucket}/{s3_url}"

        if table.exists():
            if exists == 'fail':
                raise ValueError("Table Exists")
            elif exists == 'append':
                queue = [create_copy_statement(tablename, schemaname, columns, s3_bucket_url, credentials)]
            elif exists == 'replace':
                queue = [
                    'drop table {schemaname}.{tablename}'.format(**locals()),
                    table.sql_schema(),
                    create_copy_statement(tablename, schemaname, columns, s3_bucket_url, credentials)
                ]
            elif exists == 'update':
                primary_key = args.get('primary_key')
                staging_table = '#{tablename}'.format(**locals())
                if not primary_key:
                    raise ValueError("Expected a primary_key argument, since exists='update'")
                if isinstance(primary_key, str):
                    primary_key = [primary_key]

                primary_key_hash_clause = 'md5({0})'.format(' || '.join(k for k in primary_key))
                queue = [
                    'drop table if exists {staging_table}'.format(**locals()),
                    'create table {staging_table} (like {schemaname}.{tablename})'.format(**locals()),
                    create_copy_statement(staging_table, '', columns, s3_bucket_url, credentials),
                    'delete from {schemaname}.{tablename} where {primary_key_hash_clause} in (select {primary_key_hash_clause} from {staging_table})'.format(**locals()),
                    'insert into {schemaname}.{tablename} (select * from {staging_table})'.format(**locals())
                ]
            else:
                raise ValueError("Bad option for `exists`")
        else:
            queue = [table.sql_schema(), create_copy_statement(tablename, schemaname, columns, s3_bucket_url, credentials)]

        with self.engine.begin() as con:
            for stmt in queue:
                try:
                    con.execute(stmt)
                except Exception as e:
                    print(e)
                    print('Error executing {}...'.format(stmt[:32]))

