from abc import abstractmethod
from drctrl.lib import Utils
from drctrl.lib.Exceptions import NotSpecifiedValidParam
from pathlib import Path
import pandas as pd

import importlib
import pkgutil

def get_plugin_class(io_type, plugin_type):
    modules = pkgutil.iter_modules(path=[Path(__file__).parent])

    target_module = None

    for loader, mod_name, ispkg in modules: 
        if plugin_type in mod_name and io_type in mod_name:
            target_module = mod_name
    try:
        module = importlib.import_module(f"drctrl.plugins.{target_module}")
    except ModuleNotFoundError:
        raise NotSpecifiedValidParam(f"Not found '{io_type}_ {plugin_type}' module")

    return getattr(module, f"{io_type.capitalize()}{plugin_type.capitalize()}")


class IOManager:
    def __init__(self, io_type, io_params):
        self.io_type = io_type
        plugin_type = io_params['type']

        self.io_class = get_plugin_class(io_type, plugin_type)
        self.io_instance = self.io_class(**io_params)
        self.io_instance.preprocess()

    def to_df(self):
        if not hasattr(self.io_instance, 'to_df'):
            raise TypeError(f"{plugin_type} plugin does not have to_df method")

        try:
            return self.io_instance.to_df()
        except Exception as e:
            raise NotSpecifiedValidParam('confirm input setting')

    def output(self, df):
        if not hasattr(self.io_instance, 'output'):
            raise TypeError(f"{plugin_type} plugin does not have output  method")
        try:
            return self.io_instance.output(df)
        except Exception as e:
            raise NotSpecifiedValidParam('confirm input setting')


class BaseInput:
    def __init__(self, **params):
        pass

    @abstractmethod
    def preprocess(self):
        pass

    @abstractmethod
    def to_df(self):
        return self.df
    
    def get_io_type(self):
        return 'input'
    

class BaseOutput:
    def __init__(self, **params):
        pass

    @abstractmethod
    def preprocess(self):
        pass

    @abstractmethod
    def output(self, df):
        pass

    def get_io_type(self):
        return 'output'
