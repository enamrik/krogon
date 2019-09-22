from unittest.mock import Mock, MagicMock
from krogon.logger import Logger


class MockLogger:
    def __init__(self):
        logger = Mock(spec=Logger)
        logger.add_prefix = MagicMock(name='add_prefix', return_value=logger)
        self.logger = Logger(name="test")

    def get_mock(self):
        return self.logger
