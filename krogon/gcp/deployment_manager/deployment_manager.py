from krogon.logger import Logger
from krogon.gcp.deployment_manager.deployment_template import DeploymentTemplate
from krogon.gcp.deployment_manager.deployment_status import DeploymentStatus
from typing import Any
from krogon.gcp.on_http404 import on_http404
import krogon.gcp.gcloud as gc
import krogon.yaml as yaml
import time
import krogon.either as E
import krogon.maybe as M


def new_deployment_manager(gcloud: gc.GCloud, logger: Logger):
    return gc.create_api(gcloud, name='deploymentmanager', version='v2beta') \
           | E.then | (lambda client: DeploymentManager(client, logger))


class DeploymentManager:
    def __init__(self, client, logger: Logger):
        self.logger = logger

        self.get = lambda **kwargs: \
            E.try_catch(lambda: client.deployments().get(**kwargs).execute()) \
            | E.then | (lambda r: M.Just(r)) \
            | E.catch_error | on_http404(return_result=E.Success(M.Nothing()))

        self.delete = lambda **kwargs: \
            E.try_catch(lambda: client.deployments().delete(**kwargs).execute()) \
            | E.catch_error | on_http404(return_result=E.Failure('Deployment does not exist'))

        self.update = lambda **kwargs: \
            E.try_catch(lambda: client.deployments().update(**kwargs).execute()) \
            | E.catch_error | on_http404(return_result=E.Failure('Deployment does not exist'))

        self.insert = lambda **kwargs: E.try_catch(lambda: client.deployments().insert(**kwargs).execute())


def delete(dm: DeploymentManager, project: str, deployment_name: str) -> E.Either[DeploymentStatus, Any]:
    return dm.delete(project=project,
                     deployment=deployment_name,
                     deletePolicy='DELETE') \
           | E.on | dict(success=lambda resp: dm.logger.info("RESULT: {}".format(resp))) \
           | E.then | (lambda _: _poll_status(dm, project, deployment_name))


def apply(dm: DeploymentManager, project: str, deployment_name: str, template: DeploymentTemplate) \
        -> E.Either[DeploymentStatus, Any]:

    return create_or_update(dm, project, deployment_name, create_template=template, update_template=template)


def create_or_update(dm: DeploymentManager,
                     project: str,
                     deployment_name: str,
                     create_template: DeploymentTemplate,
                     update_template: DeploymentTemplate) -> E.Either[DeploymentStatus, Any]:

    payload = lambda template: {
        'name': deployment_name,
        'description': template.description,
        'labels': template.labels,
        'target': {'config': {'content': yaml.dump(template.resources)}}
    }

    poll_status = lambda resp: E.Success(resp) \
                               | E.on | dict(success=lambda r: dm.logger.info("RESULT: {}".format(r))) \
                               | E.then | (lambda _: _poll_status(dm, project, deployment_name))

    return dm.get(project=project, deployment=deployment_name) \
           | E.then | (lambda maybe_resp:
                       maybe_resp
                       | M.from_maybe | dict(
                           if_just=lambda resp:
                               E.Success('UPDATE NOT SUPPORT for deployment: '+deployment_name+'. Skipping.')
                               if update_template.empty
                               else dm.update(project=project,
                                              deployment=deployment_name,
                                              body=dict(payload(update_template),
                                                        **{'fingerprint': resp['fingerprint']}))
                                    | E.then | poll_status,
                           if_nothing=lambda:
                               dm.insert(project=project, body=payload(create_template))
                               | E.then | poll_status)
                       )


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
                       else _poll_status(dm, project, deployment_name)) \
           | E.then | (lambda status:
                       E.Failure(status.error)
                       if status.has_error
                       else E.Success(status))


