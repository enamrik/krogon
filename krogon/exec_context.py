import krogon.file_system as f
import krogon.gcp.gcloud as g
import krogon.k8s.kubectl as k
import krogon.os as o
import krogon.either as E
import copy as c
import sys
from typing import List
from krogon.logger import Logger
from krogon.config import Config


class ExecContext:
    def __init__(self, config: Config):
        logger = Logger(name='krogon')
        fs = f.file_system()
        os = o.new_os()
        gcloud = g.new_gcloud(config, fs, os, logger)
        kubectl = k.KubeCtl(config, os, logger, gcloud, fs)

        self.fs = fs
        self.gcloud = gcloud
        self.kubectl = kubectl
        self.os = os
        self.logger = logger
        self.config = config
        self.templates = []
        self.step_state = {}

    def set_state(self, key, value):
        self.step_state[key] = value

    def get_state(self, key, ensure: bool = True):
        if key == 'project_id':
            return self.config.get_project_id(ensure)
        if key == 'service_account_info':
            return self.config.get_service_account_info(ensure)

        value = self.step_state[key] \
            if key in self.step_state \
            else None

        if ensure is True and value is None:
            raise sys.exit("State value {} missing".format(key))

        return value

    def append_templates(self, templates: List[dict]):
        self.templates = self.templates + templates

    def os_run(self, command: str) -> E.Either[str, any]:
        return self.os.run(command, self.logger)

    def copy(self):
        return c.deepcopy(self)
