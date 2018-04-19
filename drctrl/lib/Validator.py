from drctrl.lib.ConfigParser import configParser
from typing import Dict, Tuple, List

class Validator:
    def __init__(self):
        pass

    @staticmethod
    def validator(config: ConfigParser, required_params: Dict[str, bool], cmd : str):
        config_params = config.get_params[cmd]

        invalid_params = []
        for k, required in params.items():
            if required and k not in params:
                invalid_params.append(k)

        return invalid_params

    @staticmethod
    def check_environment(config:configParser):
        required_params = {
                'project_id' : True,
                'target_feature' : True,
                'metric' : True,
                'cv_method' : True,
                'validation_type' : True,
                'validation_params' : True,
                '' : True
        }




