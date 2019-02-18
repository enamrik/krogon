import os
from krogon.config import config


def build_config():
    return config(project_id=os.environ['GCP_PROJECT'],
                    service_account_b64=os.environ['GCP_SERVICE_ACCOUNT_B64'])


