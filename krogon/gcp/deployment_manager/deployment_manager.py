from googleapiclient.errors import HttpError
from krogon.logger import Logger
from krogon.gcp.deployment_manager.deployment_template import DeploymentTemplate
from krogon.gcp.deployment_manager.deployment_status import DeploymentStatus
from typing import Any, Callable
import krogon.yaml as yaml
import time
import krogon.either as E
import krogon.maybe as M


class DeploymentManager:
    def __init__(self, client, logger: Logger):
        self.logger = logger

        self.get = lambda **kwargs: \
            E.try_catch(lambda: client.deployments().get(**kwargs).execute()) \
            | E.then | (lambda r: M.Just(r)) \
            | E.catch_error | _on_http404(return_result=E.Success(M.Nothing()))

        self.delete = lambda **kwargs: \
            E.try_catch(lambda: client.deployments().delete(**kwargs).execute()) \
            | E.catch_error | _on_http404(return_result=E.Failure('Deployment does not exist'))

        self.update = lambda **kwargs: \
            E.try_catch(lambda: client.deployments().update(**kwargs).execute()) \
            | E.catch_error | _on_http404(return_result=E.Failure('Deployment does not exist'))

        self.insert = lambda **kwargs: E.try_catch(lambda: client.deployments().insert(**kwargs).execute())


def delete(dm: DeploymentManager, project: str, deployment_name: str) -> E.Either[DeploymentStatus, Any]:
    return dm.delete(project=project,
                     deployment=deployment_name,
                     deletePolicy='DELETE') \
           | E.on | dict(success=lambda resp: dm.logger.info("RESULT: {}".format(resp))) \
           | E.then | (lambda _: _poll_status(dm, project, deployment_name))


def apply(dm: DeploymentManager, project: str, deployment_name: str, template: DeploymentTemplate) -> E.Either[DeploymentStatus, Any]:

    payload = {
        'name': deployment_name,
        'description': template.description,
        'labels': template.labels,
        'target': {'config': {'content': yaml.dump(template.resources)}}
    }

    return dm.get(project=project, deployment=deployment_name) \
        | E.then | (lambda maybe_resp:
                    maybe_resp
                    | M.from_maybe | dict(
                        if_just=lambda resp: dm.update(project=project,
                                                       deployment=deployment_name,
                                                       body=dict(payload, **{'fingerprint': resp['fingerprint']})),
                        if_nothing=lambda: dm.insert(project=project, body=payload))
                    ) \
        | E.on | dict(success=lambda resp: dm.logger.info("RESULT: {}".format(resp))) \
        | E.then | (lambda _: _poll_status(dm, project, deployment_name))


def _poll_status(dm: DeploymentManager, project: str, deployment_name: str) -> E.Either[DeploymentStatus, Any]:
    return dm.get(project=project, deployment=deployment_name) \
           | E.then | (lambda maybe_resp:
                       maybe_resp
                       | M.from_maybe | dict(
                           if_just=lambda resp: DeploymentStatus(resp),
                           if_nothing=lambda: DeploymentStatus(None))
                       ) \
           | E.on | dict(success=lambda status: status.log_status(dm.logger)) \
           | E.on | dict(success=lambda status: time.sleep(5 if not status.complete else 0)) \
           | E.then | (lambda status:
                       status
                       if status.complete
                       else _poll_status(dm, project, deployment_name))


def _on_http404(return_result: E.Either) -> Callable[[Exception], E.Either]:
    def handle(ex: E.TryCatchError):
        if not (hasattr(ex.caught_error, 'resp') and hasattr(ex.caught_error.resp, 'status')):
            return E.Failure(ex)

        http_error: HttpError = ex.caught_error
        if http_error.resp.status == 404:
            return return_result
        else:
            return E.Failure(ex)

    return handle
