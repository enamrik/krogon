import krogon.either as E
from typing import Any


class EitherMatcher:
    def __init__(self, result: E.Either):
        self.result = result

    def succeeded(self):
        assert type(self.result) == E.Success, "Should have succeeded. Instead got: {}".format(self.result)

    def failed(self):
        assert type(self.result) == E.Failure, "Should have failed. Instead got: {}".format(self.result)

    def succeeded_with(self, value: Any):
        self.succeeded()
        success: E.Success = self.result
        assert success.value == value, "Expected succeed with: {}. Instead got: {}" \
            .format(value, success.value)

    def failed_with(self, error: Any):
        self.failed()
        failure: E.Failure = self.result
        assert failure.value == error, "Expected to fail with: {}. Instead got: {}" \
            .format(error, failure.value)


def assert_that(result: E.Either):
    return EitherMatcher(result)


