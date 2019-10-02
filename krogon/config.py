from base64 import b64decode
from typing import Optional
import sys
import krogon.file_system as f
import krogon.os as o
import json


def config(project_id: Optional[str] = None,
           service_account_b64: Optional[str] = None,
           output_template: Optional[bool] = None,
           delete: Optional[bool] = None):
    fs = f.file_system()
    os = o.new_os()
    krogon_version = fs.read(fs.path_rel_to_app_dir('./VERSION')).strip()
    krogon_url = fs.read(fs.path_rel_to_app_dir('./URL')).strip()
    krogon_install_url = '{}@{}##egg=krogon'.format(krogon_url, krogon_version)
    cache_dir = fs.cwd() + '/' + Config.cache_folder_name()
    scripts_dir = fs.path_rel_to_file('./' + Config.scripts_folder_name(), __file__)
    output_dir = fs.cwd() + '/' + Config.output_folder_name()

    fs.ensure_path(cache_dir)
    fs.ensure_path(output_dir)

    delete = _get_arg(os, 'KG_DELETE', delete, default=False, transform=_parse_bool)
    output_template = _get_arg(os, 'KG_TEMPLATE', output_template, default=False, transform=_parse_bool)

    return Config(project_id,
                  service_account_b64,
                  krogon_version,
                  krogon_install_url,
                  cache_dir,
                  output_dir,
                  scripts_dir,
                  output_template,
                  delete,
                  os)


def _parse_bool(v):
    if type(v) == str:
        return v.lower() in ("yes", "true", "1")
    else:
        return bool(v)


class Config:
    def __init__(self,
                 project_id: str,
                 service_account_b64: str,
                 krogon_version: str,
                 krogon_install_url: str,
                 cache_dir: str,
                 output_dir,
                 scripts_dir: str,
                 output_template: bool,
                 deleting: bool,
                 os: o.OS):
        self.deleting = deleting
        self.output_template = output_template
        self.project_id = project_id
        self.krogon_version = krogon_version
        self.krogon_install_url = krogon_install_url
        self.service_account_b64 = service_account_b64
        self.cache_dir = cache_dir
        self.output_dir = output_dir
        self.scripts_dir = scripts_dir
        self.service_account_file = cache_dir + '/service_account.json'
        self.os = os

    def get_service_account_b64(self, ensure: bool = True):
        return _get_arg(self.os, 'KG_SERVICE_ACCOUNT_B64', self.service_account_b64, ensure=ensure)

    def get_project_id(self, ensure: bool = True):
        return _get_arg(self.os, 'KG_PROJECT_ID', self.project_id, ensure=ensure)

    def get_service_account_info(self, ensure: bool = True):
        b64_str = self.get_service_account_b64(ensure=ensure)
        if b64_str is None:
            return None
        return json.loads(b64decode(b64_str).decode("utf-8"))

    @staticmethod
    def output_folder_name():
        return 'output'

    @staticmethod
    def cache_folder_name():
        return '.infra_cache'

    @staticmethod
    def scripts_folder_name():
        return 'scripts'


def _get_arg(os: o.OS, key, value, ensure=False, default=None, transform=(lambda x: x)):
    value = os.get_env(key) if value is None else value
    value = default if value is None else value
    if value is None and ensure is True:
        return sys.exit("MISSING arg {}".format(key))
    else:
        return transform(value)
