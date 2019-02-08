from typing import Optional
from krogon.logger import Logger


class DeploymentStatus:
    def __init__(self, status: Optional[dict]):
        self.status = status

        if self.status is None:
            self.complete = True
            self.has_error = False
            self.status_message = 'Stack deleted'
        else:
            operation = self.status['operation']
            self.complete = operation['status'] == 'DONE'
            error = operation['error'] if 'error' in operation else None
            self.has_error = error is not None

            self.status_message = 'status: {}, progress: {}, op: {}, error: {}' \
                .format(operation['status'], operation['progress'], operation['operationType'], error)

    def log_status(self, logger: Logger) -> None:
        level = 'error' if self.has_error else 'info'
        logger.log(level, self.status_message)

