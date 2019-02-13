from unittest.mock import MagicMock
from krogon.krogon import Krogon
from krogon.config import Config
from base64 import b64encode
from krogon.steps.step import GenericStep
from krogon.steps.steps import steps
from krogon.steps.step_context import StepContext
from tests.helpers import MockLogger, MockGCloud, MockFileSystem, MockOsSystem
import krogon.either as E
import tests.helpers.assert_either as e
import json


def test_can_run_steps():
    config = Config("project1", b64encode(json.dumps({'key': 'someKey'}).encode('utf-8')), '1.0.0')
    file_system = MockFileSystem()
    gcloud = MockGCloud()
    os_system = MockOsSystem()
    logger = MockLogger()
    mock_method_1 = MagicMock(name='mock_method_1')
    mock_method_2 = MagicMock(name='mock_method_1')
    step_1_value = 'someValue1'
    step_2_value = 'someValue2'
    mock_method_1.return_value = E.Success(step_1_value)
    mock_method_2.return_value = E.Success(step_2_value)
    step_1 = GenericStep('my-step-1', mock_method_1)
    step_2 = GenericStep('my-step-2', mock_method_2)
    expected_result = StepContext({step_1.name: step_1_value, step_2.name: step_2_value})

    result = Krogon(logger.get_mock(), os_system.get_mock(), gcloud.get_mock(), file_system.get_mock())\
        .exec(config, steps(step_1, step_2))

    mock_method_1.assert_called()
    mock_method_2.assert_called()
    e.assert_that(result).succeeded_with(expected_result)
