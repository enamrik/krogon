import krogon.either as E
import sys
from typing import List
from krogon.k8s.kubectl import KubeCtl
from krogon.logger import Logger
from krogon.config import Config


class TemplateContext:
    def __init__(self, config: Config, kubectl: KubeCtl, state=None):
        self.templates = []
        self.kubectl = kubectl
        self.config = config

        if state is None:
            state = {}
        self._state = state

        self._fs = config.fs
        self._os = config.os
        self._logger = Logger(name='krogon')

    @staticmethod
    def new_from_state(ctx: 'TemplateContext') -> 'TemplateContext':
        return TemplateContext(ctx.config, ctx.kubectl, ctx._state)

    def os_run(self, command: str) -> E.Either[str, any]:
        return self._os.run(command, self._logger)

    def set_state(self, key, value):
        self._state[key] = value

    def get_state(self, key, ensure: bool = False):
        value = self._state[key] \
            if key in self._state \
            else None

        if ensure is True and value is None:
            raise sys.exit("State value {} missing".format(key))

        return value

    def append_templates(self, templates: List[dict]):
        self.templates = self.templates + templates


