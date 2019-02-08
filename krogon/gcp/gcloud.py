from typing import Callable, Any
from google.oauth2 import service_account
from apiclient.discovery import build
from krogon.logger import Logger
import krogon.either as E
from krogon.gcp.deployment_manager.deployment_manager import DeploymentManager


class GCloud:
    def __init__(self,
                 service_account_info: dict,
                 init_client: Callable[[str, str, dict], Any]):
        self.init_client = init_client
        self.service_account_info = service_account_info

    def deployment_manager(self, logger: Logger):
        return self.init_client('deploymentmanager', 'v2beta', self.service_account_info) \
         | E.then | (lambda client: DeploymentManager(client, logger))


def new_gcloud(service_account_info: dict):
    def init_client(api: str, version: str, service_acc_info: dict) -> Any:
        return E.try_catch(lambda: service_account.Credentials.from_service_account_info(service_acc_info)) \
        | E.then | (lambda credentials: E.try_catch(lambda: build(api, version, credentials=credentials, cache_discovery=False)))

    return GCloud(service_account_info, init_client)
