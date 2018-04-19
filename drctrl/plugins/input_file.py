import pandas as pd
from pathlib import Path
from drctrl.plugins.base import BaseInput
import inspect

class InputFile(BaseInput):
    def __init__(self, path, filename, **kwargs):
        self.path = Path(path)
        self.filename = Path(filename)
        self.params = kwargs

        args = inspect.getargspec(pd.read_csv).args
        params = {}
        for k, v in self.params.items():
            if k in args:
                params[k] = v
        self.params = params


    def to_df(self):
        return pd.read_csv(self.path.joinpath(self.filename), **self.params)

