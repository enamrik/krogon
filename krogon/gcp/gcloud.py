from typing import Callable, Any
from google.oauth2 import service_account
from apiclient.discovery import build
import krogon.either as E


class GCloud:
    def __init__(self,
                 service_account_info: dict,
                 init_client: Callable[[str, str, dict], Any]):
        self.init_client = init_client
        self.service_account_info = service_account_info


def create_api(gcloud: GCloud, name: str, version: str):
    return gcloud.init_client(name, version, gcloud.service_account_info)


def new_gcloud(service_account_info: dict):
    def init_client(api: str, version: str, service_acc_info: dict) -> Any:
        return E.try_catch(lambda: service_account.Credentials.from_service_account_info(service_acc_info)) \
        | E.then | (lambda credentials: E.try_catch(lambda: build(api, version, credentials=credentials, cache_discovery=False)))

    return GCloud(service_account_info, init_client)
