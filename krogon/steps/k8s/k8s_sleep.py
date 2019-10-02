import time
from krogon.exec_context import ExecContext


class K8sSleep:
    def __init__(self, seconds: float):
        self.seconds = seconds

    def map_context(self, context: ExecContext) -> ExecContext:
        if not context.config.output_template:
            context.logger.info("Sleeping for {}s".format(self.seconds))
            time.sleep(self.seconds)
        return context

    def __str__(self):
        return "K8sSleep({})".format(self.seconds)


def sleep(seconds: float) -> K8sSleep:
    return K8sSleep(seconds)


