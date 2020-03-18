import sys
import krogon.file_system as f
import krogon.os as o
import traceback
from krogon.logger import Logger


def config():
    fs = f.file_system()
    os = o.new_os()
    logger = Logger(name='krogon')
    krogon_version = fs.read(fs.path_rel_to_app_dir('./VERSION')).strip()
    krogon_url = fs.read(fs.path_rel_to_app_dir('./URL')).strip()
    krogon_install_url = '{}@{}##egg=krogon'.format(krogon_url, krogon_version)
    cache_dir = fs.cwd() + '/' + Config.cache_folder_name()
    scripts_dir = fs.path_rel_to_file('./' + Config.scripts_folder_name(), __file__)
    output_dir = fs.cwd() + '/' + Config.output_folder_name()

    fs.ensure_path(cache_dir)
    fs.ensure_path(output_dir)

    delete = os.get_env('KG_DELETE')
    output_template = os.get_env('KG_TEMPLATE')

    return Config(krogon_version,
                  krogon_install_url,
                  cache_dir,
                  output_dir,
                  scripts_dir,
                  output_template,
                  delete,
                  os,
                  fs,
                  logger)


class Config:
    def __init__(self,
                 krogon_version: str,
                 krogon_install_url: str,
                 cache_dir: str,
                 output_dir,
                 scripts_dir: str,
                 output_template: bool,
                 deleting: bool,
                 os: o.OS,
                 fs: f.FileSystem,
                 log: Logger):

        self.deleting = deleting
        self.output_template = output_template
        self.krogon_version = krogon_version
        self.krogon_install_url = krogon_install_url
        self.cache_dir = cache_dir
        self.output_dir = output_dir
        self.scripts_dir = scripts_dir
        self.service_account_file = cache_dir + '/service_account.json'
        self.os = os
        self.os_run = lambda cmd: os.run(cmd, log)
        self.fs = fs
        self.log = log

    def has_arg(self, key):
        return self.get_arg(key, None) is not None

    def get_arg(self, key, value=None, ensure=False, default=None, transform=(lambda x: x)):
        value = self.os.get_env(key) if value is None else value
        value = default if value is None else value
        if value is None and ensure is True:
            traceback.print_stack()
            return sys.exit("MISSING arg {}".format(key))
        else:
            return transform(value)

    @staticmethod
    def output_folder_name():
        return 'output'

    @staticmethod
    def cache_folder_name():
        return '.infra_cache'

    @staticmethod
    def scripts_folder_name():
        return 'scripts'


def parse_bool(v):
    if type(v) == str:
        return v.lower() in ("yes", "true", "1")
    else:
        return bool(v)


