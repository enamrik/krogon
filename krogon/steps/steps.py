from typing import List
from krogon.either_ext import pipeline
from krogon.steps.step_context import StepContext
from krogon.config import Config
from krogon.logger import Logger
from krogon.steps.step import Step, GenericStep
from krogon.steps.gclb.gclb_step import GclbStep
from krogon.steps.deploy.deployment_manager_step import DeploymentManagerStep
from krogon.ci.gocd.deploy_gocd import DeployGoCD
from krogon.steps.deploy_in_clusters.k8s_step import K8sStep
from krogon.k8s.kubectl import KubeCtl
from krogon.vault.vault import Vault
from krogon.istio.istio import Istio
import krogon.kubemci.kubemci as km
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

    def _exec_step(step: Step, _cur_context: StepContext):
        logger.step(step.name)
        step_logger = logger.add_prefix(step.name)
        kubectl = KubeCtl(config, os_system, step_logger, gcloud, file_system)
        kubemci = km.KubeMci(config, os_system, step_logger, gcloud, file_system)
        vault = Vault(kubectl)
        istio = Istio(config, os_system, step_logger, gcloud, file_system, kubectl)
        d_gocd = DeployGoCD(kubectl, file_system)

        if type(step) == GclbStep:
            cur_step: GclbStep = step
            return cur_step.exec(kubemci)

        elif type(step) == DeploymentManagerStep:
            cur_step: DeploymentManagerStep = step
            return cur_step.exec(d_gocd, vault, istio, gcloud, config, step_logger)

        elif type(step) == GenericStep:
            cur_step: GenericStep = step
            return cur_step.exec()

        elif type(step) == K8sStep:
            cur_step: K8sStep = step
            return cur_step.exec(kubectl)
        else:
            return E.Failure("Unsupported step type: {}".format(step))

    def _handle_next_step(step: Step):
        def _step_runner(cur_context: StepContext):
            return _exec_step(step, cur_context) \
                    | E.then | (lambda step_result: cur_context.set_param(step.name, step_result))
        return _step_runner

    step_funcs = list(map(_handle_next_step, cur_steps.steps_list))
    return pipeline(step_funcs, StepContext(params={}))

