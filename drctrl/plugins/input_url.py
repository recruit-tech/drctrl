import pandas as pd
from pathlib import Path
from drctrl.plugins.base import BaseInput
import inspect
from drctrl.lib import Utils

class InputUrl(BaseInput):
    def __init__(self, url, **kwargs):
        self.url = url
        self.params = kwargs

        self.params = kwargs

        args = inspect.getargspec(pd.read_csv).args
        params = {}
        for k, v in self.params.items():
            if k in args:
                params[k] = v

        self.params = params

    def preprocess(self):
        self.filename = Utils.fetch_file(self.url, './')

    def to_df(self):
        return pd.read_csv(self.filename, **self.params)

