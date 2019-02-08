from base64 import b64decode
import json


class Config:
    def __init__(self, project_id, service_account_b64):
        self.project_id = project_id
        self.service_account_info = json.loads(b64decode(service_account_b64).decode("utf-8"))


def config(project_id, service_account_b64):
    return Config(project_id, service_account_b64)
