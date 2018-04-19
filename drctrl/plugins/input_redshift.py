import pandas as pd
from drctrl.plugins.base import BaseInput
from drctrl.lib.rsdf import rsdf


class InputRedshift(BaseInput):
    def __init__(self, dbname, host, port, user, password,
            schema, table, **kwargs):

        self.dbname = dbname
        self.host = host
        self.port = port
        self.user = user
        self.password = password

        self.schema = schema
        self.table  = table

        self.params = kwargs

    def preprocess(self):
        pass

    def to_df(self):
        client = rsdf(user=self.user,
                password=self.password,
                dbname=self.dbname,
                host=self.host,
                port=self.port)


        df = client.query_to_df(f"select * from {self.schema}.{self.table}")

        return df

