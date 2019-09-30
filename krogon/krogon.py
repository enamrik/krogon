from typing import List
from krogon.config import Config
from krogon.exec_context import ExecContext
from krogon.either_ext import chain
import krogon.config as c
import krogon.either as E
import sys


def krogon(run_steps: List, for_config: Config = None):
    config = for_config if for_config is not None else c.config()
    context = ExecContext(config)
    logger = context.logger

    logger.info("KROGON:")
    logger.info("version: {}".format(config.krogon_version))
    logger.info("project: {}".format(config.get_project_id()))

    def _exec_step(step):
        if config.deleting:
            return step["delete"](context) if "delete" in step else E.success()
        else:
            return step["exec"](context)

    return chain(run_steps, _exec_step) \
           | E.on | dict(success=lambda _: logger.info('DONE'),
                         failure=lambda e: logger.error('FAILED: {}'.format(e))) \
           | E.on | dict(failure=lambda e: sys.exit(1))
