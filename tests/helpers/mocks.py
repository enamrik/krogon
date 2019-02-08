from typing import List, Any
import re


class RaiseException:
    def __init__(self, exception: Exception):
        self.exception = exception


class Setup:
    def __init__(self,
                 args=None, kwargs=None,
                 return_values: List[Any] = None,
                 strict=False):
        self.strict = strict
        self.return_values = return_values if return_values is not None else []
        self.args = args
        self.kwargs = kwargs
        self.calls = []

        if len(self.return_values) == 0:
            raise Exception("SETUP.init: Return values cannot be empty")

    def __str__(self):
        return "args: {}, kwargs: {}, return_values: {}, strict: {}".format(self.args, self.kwargs, self.return_values, self.strict)

    def append_call(self, call_args):
        self.calls.append(call_args)

    def expected_to_have_been_called(self, times=None, exactly_times=None):
        times = times if times is not None else 1

        exactly_text = 'exactly' if exactly_times is not None else ''
        exp = len(self.calls) == times if exactly_times is not None else len(self.calls) >= times

        assert exp, "Expected to be called {} {} times. But call count was: {}"\
            .format(exactly_text, times, len(self.calls))

    def expected_not_to_have_been_called(self):
        assert len(self.calls) == 0, "Expected to not be called. But call count was: {}" \
            .format(len(self.calls))


class MockSetup:
    @staticmethod
    def mock_name(mock):
        return re.search(r'<.*Mock name=\'([a-zA-Z0-9._]+)\'', str(mock), re.IGNORECASE).group(1)

    @staticmethod
    def mock(mock, setups: List[Setup]):
        setup_return_history = {}

        def side_effect(*args, **kwargs):
            for cur_setup in setups:
                setup: Setup = cur_setup
                match = True
                strict = setup.strict
                setup_args = setup.args
                setup_kwargs = setup.kwargs

                if setup_args is not None:
                    if len(setup_args) != len(args) and strict is True:
                        match = False
                    if match:
                        for idx, arg in enumerate(args):
                            if idx <= len(setup_args) - 1 \
                                    and setup_args[idx] != arg \
                                    and setup_args[idx] != MockSetup.any():
                                match = False
                                break

                if setup_kwargs is not None:
                    if len(setup_kwargs.keys()) != len(kwargs.keys()) and strict is True:
                        match = False
                    if match:
                        for key, value in kwargs.items():
                            if key in setup_kwargs \
                                    and setup_kwargs[key] != value \
                                    and setup_kwargs[key] != MockSetup.any():
                                match = False
                                break
                if match:
                    return_index = setup_return_history[id(setup)] \
                        if id(setup) in setup_return_history \
                        else 0
                    if return_index < len(setup.return_values):
                        setup_return_history[id(setup)] = return_index + 1
                        return_value = setup.return_values[return_index]
                    else:
                        return_value = setup.return_values[-1]

                    setup.append_call(dict(method=MockSetup.mock_name(mock), args=args, kwargs=kwargs))

                    if type(return_value) is RaiseException:
                        raise_exception: RaiseException = return_value
                        raise raise_exception.exception

                    return return_value

            raise Exception('NO MATCH FOUND in {} for method: args:{}, kwargs:{}, setups: {}'
                            .format(mock, args, kwargs, list(map(str, setups))))

        mock.side_effect = side_effect
        return mock

    @staticmethod
    def any():
        return '<Any>'
