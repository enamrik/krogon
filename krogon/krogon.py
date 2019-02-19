from krogon.config import Config
from krogon.logger import Logger
import krogon.steps.steps as s
import krogon.file_system as fs
import krogon.gcp.gcloud as gcp
import krogon.os as os
import krogon.either as E


def krogon(config: Config, steps: s.Steps):
    file_system = fs.file_system()
    os_system = os.new_os()
    logger = Logger(name='krogon')
    gcloud = gcp.new_gcloud(config, file_system, os_system, logger)

    return Krogon(logger, os_system, gcloud, file_system).exec(config, steps)


class Krogon:
    def __init__(self,
                 logger: Logger,
                 os_system: os.OS,
                 gcloud: gcp.GCloud,
                 file_system: fs.FileSystem):

        self.logger = logger
        self.os_system = os_system
        self.gcloud = gcloud
        self.file_system = file_system

    def exec(self, config: Config, steps: s.Steps):
        return s.exec_steps(steps, config, self.logger, self.os_system, self.gcloud, self.file_system) \
               | E.on | dict(success=lambda _: self.logger.info('DONE'),
                             failure=lambda e: self.logger.error('FAILED: {}'.format(e))) \
               | E.on | dict(failure=lambda e: exit(1))
