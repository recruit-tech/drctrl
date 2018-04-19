import yaml
import os
import jinja2
import tempfile
import pathlib
from pykwalify.core import Core
from pykwalify.errors import SchemaError
from drctrl.lib.Exceptions import NotSufficientParams
from drctrl.lib.Utils import suppressStdOutput, suppressStdError
import logging

# stop pykwalify log
logging.getLogger("pykwalify.core").setLevel('CRITICAL')

schema_path = f"{pathlib.Path(__file__).parents[0]}/schema"

class Validator:
    def __init__(self):
        pass

    @staticmethod
    def validate(target): # : dict
        return Validator.validate_with(schema='base_schema', target=target)
    
    @staticmethod
    def validate_with(schema, target, raise_exception=True):
        validator = Core(source_data=target, schema_files=[f"{schema_path}/{schema}.yml"])

        return validator.validate(raise_exception=raise_exception)

class configParser:
    # config: configure yaml
    def __init__(self, file_path):
        self.validator = Validator()
        self.file_path = file_path

        if configParser.is_tmpl(file_path):
            self.config = yaml.load(configParser.parse_tmpl(file_path))
        else:
            self.config = yaml.load(open(file_path, 'r'))

    @staticmethod
    def is_tmpl(file_path):
        return file_path.split('.')[-1] == 'tmpl'

    @staticmethod
    def parse_tmpl(file_path):
        tmpl = jinja2.Template(open(file_path, 'r').read())
        return tmpl.render(env=os.environ)

    def is_valid(self, cmds=None):
        if cmds is None:
            cmds = []

        for cmd in cmds + ['environment']:
            if self.get_params(cmd=cmd) is None:
                raise NotSufficientParams(f"{cmd} command is not supplied in configuration file")

        try:
            self.validator.validate_with(schema='project_id_is_supplied',
                    target=self.config,
                    raise_exception=True)
        except SchemaError as e:
            # project_id is not supplied
            try:
                self.validator.validate(self.config)
            except SchemaError as e:
                print(e.msg)
                print(f"Check your configuration file : {self.file_path}")
                return False


        return True

    def get_params(self, cmd):
        if cmd not in self.config:
            return None

        return self.config[cmd]

    def set_params(self, cmd=None, params=None):
        if cmd not in self.config:
            raise NotSetEnvironmentException(f"not set {cmd} parameter")

        for k, v in params.items():
            self.config[cmd][k] = v

    def get_param(self, cmd, param):
        if cmd not in self.config:
            return None
        if param not in self.config[cmd]:
            return None

        return self.config[cmd][param]


