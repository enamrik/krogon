from base64 import b64decode
import krogon.file_system as fs
import json


def config(project_id, service_account_b64):
    file_system = fs.file_system()
    krogon_version = file_system.read(file_system.path_rel_to_app_dir('./VERSION')).strip()

    cache_dir = file_system.cwd() + '/' + Config.cache_folder_name()
    scripts_dir = file_system.path_rel_to_file('./'+Config.scripts_folder_name(), __file__)

    if not file_system.exists(cache_dir):
        file_system.mkdir(cache_dir)

    return Config(project_id,
                  service_account_b64,
                  krogon_version,
                  cache_dir,
                  scripts_dir)


class Config:
    def __init__(self, project_id: str,
                 service_account_b64: str,
                 krogon_version: str,
                 cache_dir: str,
                 scripts_dir: str):

        self.project_id = project_id
        self.krogon_version = krogon_version
        self.service_account_b64 = service_account_b64
        self.service_account_info = json.loads(b64decode(service_account_b64).decode("utf-8"))
        self.cache_dir = cache_dir
        self.scripts_dir = scripts_dir
        self.service_account_file = cache_dir + '/service_account.json'

    @staticmethod
    def cache_folder_name():
        return '.infra_cache'

    @staticmethod
    def scripts_folder_name():
        return 'scripts'
