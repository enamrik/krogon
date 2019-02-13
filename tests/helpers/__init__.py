from .mock_logger import MockLogger
from unittest.mock import patch
from .mock_os_system import MockOsSystem
from .mock_file_system import MockFileSystem
from .mock_gcloud import MockGCloud
from typing import Callable
import traceback
import click.testing
from .mocks import MockSetup, Setup


def mock_krogon_cli(call_cli: Callable, env: dict):
    file_system = MockFileSystem()
    gcloud = MockGCloud()
    os_system = MockOsSystem()
    logger = MockLogger()
    cli_runner = click.testing.CliRunner()

    with patch('time.sleep', return_value=None), \
         patch.dict('os.environ', env), \
         patch('krogon.file_system.file_system', return_value=file_system.get_mock()), \
         patch('krogon.os.new_os', return_value=os_system.get_mock()), \
         patch('krogon.logger.Logger', return_value=logger.get_mock()), \
         patch('krogon.gcp.gcloud.new_gcloud', return_value=gcloud.get_mock()):

        def _cli_assert(result):
            print("CLI-STDOUT:\n", result.stdout_bytes.decode("utf-8"))
            if result.exception is not None:
                print("CLI-ERROR:", result.exception)
                traceback.print_tb(result.exc_info[2])
                raise result.exception

        return call_cli(dict(file_system=file_system,
                             gcloud=gcloud, os_system=os_system,
                             logger=logger,
                             cli_runner=cli_runner,
                             cli_assert=_cli_assert))


def mock_krogon_dsl(call_dsl: Callable):
    file_system = MockFileSystem()
    gcloud = MockGCloud()
    os_system = MockOsSystem()
    logger = MockLogger()

    with patch('time.sleep', return_value=None), \
         patch('krogon.file_system.file_system', return_value=file_system.get_mock()), \
         patch('krogon.os.new_os', return_value=os_system.get_mock()), \
         patch('krogon.logger.Logger', return_value=logger.get_mock()), \
         patch('krogon.gcp.gcloud.new_gcloud', return_value=gcloud.get_mock()):

        return call_dsl(dict(file_system=file_system, gcloud=gcloud, os_system=os_system, logger=logger))




