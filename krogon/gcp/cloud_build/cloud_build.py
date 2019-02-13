import krogon.gcp.gcloud as gc
import krogon.either as E
import krogon.maybe as M
import time
from krogon.logger import Logger
from krogon.gcp.on_http404 import on_http404
from typing import Any


def new_cloud_build(gcloud: gc.GCloud, logger: Logger):
    return gc.create_api(gcloud, name='cloudbuild', version='v1') \
           | E.then | (lambda client: CloudBuild(client, logger))


class CloudBuild:
    def __init__(self, client, logger: Logger):
        self.client = client
        self.logger = logger

        self.get_build = lambda **kwargs: \
            E.try_catch(lambda: client.projects().builds().get(**kwargs).execute()) \
            | E.then | (lambda r: M.Just(r)) \
            | E.catch_error | on_http404(return_result=E.Success(M.Nothing()))

        self.create_build = lambda **kwargs: \
            E.try_catch(lambda: client.projects().builds().create(**kwargs).execute())


def create(cb: CloudBuild, project_id: str, template: dict):
    return cb.create_build(projectId=project_id, body=template) \
           | E.on | dict(success=lambda resp: cb.logger.info('Started build: https://console.cloud.google.com/'
                                                             'cloud-build/builds/{}'
                                                             .format(resp['metadata']['build']['id']))) \
           | E.then | (lambda resp: _poll_status(cb, resp['metadata']['build']['id'], project_id))


def _poll_status(cb: CloudBuild, build_id: str, project_id: str) -> E.Either[str, Any]:
    def _status_to_either(status: str):
        if status == 'SUCCESS':
            return E.Success()
        elif status == 'FAILURE':
            return E.Failure('Build failed')

    return cb.get_build(projectId=project_id, id=build_id) \
           | E.then | (lambda maybe_resp:
                       maybe_resp
                       | M.from_maybe | dict(
                           if_just=lambda resp: resp['status'],
                           if_nothing=lambda: None)
                       ) \
           | E.on | dict(success=lambda status: cb.logger.info('Waiting on build: {}, {}'.format(build_id, status))) \
           | E.on | dict(success=lambda status: time.sleep(5 if status == 'WORKING' else 0)) \
           | E.then | (lambda status:
                       _poll_status(cb, build_id, project_id)
                       if status == 'WORKING'
                       else _status_to_either(status))





