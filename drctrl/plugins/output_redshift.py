import pandas as pd
from drctrl.plugins.base import BaseOutput
from drctrl.lib.rsdf import rsdf

class OutputRedshift(BaseOutput):
    def __init__(self, aws_key_id, aws_secret_key, bucket, 
            dbname, host, port, user, password,
            schema=None, table=None, **kwargs):

        # s3
        self.aws_key_id = aws_key_id
        self.aws_secret_key = aws_secret_key
        self.bucket = bucket

        # redshift
        self.dbname = dbname
        self.host = host
        self.port = port
        self.user = user
        self.password = password

        self.schema = schema
        self.table  = table

    def preprocess(self):
        pass

    def output(self, df, exists='replace'):
        client = rsdf(user=self.user,
                password=self.password,
                dbname=self.dbname,
                host=self.host,
                port=self.port)

        client.load_dataframe(df, tablename=self.table, schemaname=self.schema,
                exists=exists, aws_access_key_id=self.aws_key_id, aws_secret_access_key=self.aws_secret_key,
                s3_bucket=self.bucket)

        return True

