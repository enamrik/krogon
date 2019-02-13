from base64 import b64decode
import krogon.file_system as fs
import json


class Config:
    def __init__(self, project_id: str, service_account_b64: str, krogon_version: str):
        self.project_id = project_id
        self.krogon_version = krogon_version
        self.service_account_b64 = service_account_b64
        self.service_account_info = json.loads(b64decode(service_account_b64).decode("utf-8"))


def config(project_id, service_account_b64):
    file_system = fs.file_system()
    krogon_version = file_system.read(file_system.path_rel_to_app_dir('./VERSION')).strip()
    return Config(project_id, service_account_b64, krogon_version)
