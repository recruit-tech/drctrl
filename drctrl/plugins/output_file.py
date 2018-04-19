import pandas as pd
from pathlib import Path
from drctrl.plugins.base import BaseOutput
import inspect

class OutputFile(BaseOutput):
    def __init__(self, path, filename,
            delimiter=',', index=False, escapechar='\\', **kwargs):
        self.path = Path(path)
        self.filename       = Path(filename)

        params = {}
        params['sep']       = delimiter
        params['index']     = index
        args = inspect.getargspec(pd.DataFrame.to_csv).args
        for k, v in kwargs.items():
            if k in args:
                params[k] = v

        self.params = params

    def preprocess(self):
        pass

    def output(self, df):
        df.to_csv(self.path.joinpath(self.filename), **self.params)
