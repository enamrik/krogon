import krogon.file_system as f
import krogon.gcp.gcloud as g
import krogon.k8s.kubectl as k
import krogon.os as o
import python_either.either as E
from krogon.logger import Logger
from krogon.config import Config


class ExecContext:
    def __init__(self, config: Config):
        logger = Logger(name='krogon')
        fs = f.file_system()
        os = o.new_os()
        gcloud = g.new_gcloud(config, fs, os, logger)
        kubectl = k.KubeCtl(config, os, logger, gcloud, fs)

        self.fs = fs
        self.gcloud = gcloud
        self.kubectl = kubectl
        self.os = os
        self.logger = logger
        self.config = config

    def os_run(self, command: str) -> E.Either[str, any]:
        return self.os.run(command, self.logger)
