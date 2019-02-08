from typing import List
from krogon.either_ext import pipeline
from krogon.steps.step_context import StepContext
from krogon.config import Config
from krogon.logger import Logger
from krogon.steps.step import Step, GenericStep
from krogon.steps.gclb import GclbStep
from krogon.steps.deploy import DeploymentManagerStep
from krogon.steps.k8s import K8sStep
import krogon.scripts.scripter as scp
import krogon.file_system as fs
import krogon.gcp.gcloud as gcp
import krogon.os as os
import krogon.either as E


def steps(*step_list: Step):
    return Steps(list(step_list))


class Steps:
    def __init__(self, steps_list: List[Step]):
        self.steps_list = steps_list


def exec_steps(cur_steps: Steps,
               config: Config,
               logger: Logger,
               os_system: os.OS,
               gcloud: gcp.GCloud,
               file_system: fs.FileSystem):

    scripter = lambda step_logger: \
        scp.Scripter(config.project_id, config.service_account_info, os_system, file_system, step_logger)

    def _exec_step(step: Step, _cur_context: StepContext):
        logger.info('STEP: {}'.format(step.name))
        step_logger = logger.add_prefix(step.name)

        if type(step) == GclbStep:
            cur_step: GclbStep = step
            return cur_step.exec(scripter(step_logger))

        elif type(step) == DeploymentManagerStep:
            cur_step: DeploymentManagerStep = step
            return cur_step.exec(scripter(step_logger), gcloud, config, step_logger)

        elif type(step) == GenericStep:
            cur_step: GenericStep = step
            return cur_step.exec()

        elif type(step) == K8sStep:
            cur_step: K8sStep = step
            return cur_step.exec(scripter(step_logger), file_system)
        else:
            return E.Failure("Unsupported step type: {}".format(step))

    def _handle_next_step(step: Step):
        def _step_runner(cur_context: StepContext):
            return _exec_step(step, cur_context) \
                    | E.then | (lambda step_result: cur_context.set_param(step.name, step_result))
        return _step_runner

    step_funcs = list(map(_handle_next_step, cur_steps.steps_list))
    return pipeline(step_funcs, StepContext(params={}))

