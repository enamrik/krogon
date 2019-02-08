from subprocess import Popen, PIPE
from krogon.logger import Logger
from typing import Callable, Any
import krogon.either as E
import platform


class OS:
    def __init__(self,
                 run: Callable[[str, Logger], E.Either[Any, Any]],
                 is_macos: Callable[[], bool]):
        self.run = run
        self.is_macos = is_macos


def os():
    def is_macos():
        return platform.system() == 'Darwin'

    def os_run(command, log: Logger):
        log.debug("OS_RUN: {}".format(command))
        process = Popen(command, stdout=PIPE, stderr=PIPE, shell=True)
        output = []

        for line in iter(process.stdout.readline, 'b'):
            if line == b'':
                break

            line = line.rstrip().decode("utf-8")
            print(line)
            output.append(line)

        for line in iter(process.stderr.readline, 'b'):
            if line == b'':
                break
            line = line.rstrip().decode("utf-8")
            log.error("OS_RUN: {}".format(line))

        process.communicate()

        if process.returncode != 0:
            return E.Failure("ErrorCode: " + str(process.returncode))

        return E.Success('\n'.join(output))

    return OS(os_run, is_macos)
