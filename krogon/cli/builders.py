import os
import krogon.config as c
import krogon.os as krogon_os
import krogon.file_system as fs
from krogon.logger import Logger
import krogon.scripts.scripter as scp


def build_config():
    return c.config(project_id=os.environ['GCP_PROJECT'],
                    service_account_b64=os.environ['GCP_SERVICE_ACCOUNT_B64'])


def build_scripter(config: c.Config, logger: Logger):
    file_system = fs.file_system()
    os_system = krogon_os.new_os()
    return scp.Scripter(config.project_id, config.service_account_info, os_system, file_system, logger)


