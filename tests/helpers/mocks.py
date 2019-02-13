from typing import List, Any, Optional, Callable
from tests.helpers.assert_diff import same_dict
from unittest.mock import Mock
from difflib import ndiff
import re


class RaiseException:
    def __init__(self, exception: Exception):
        self.exception = exception


class Setup:
    def __init__(self,
                 args=None,
                 kwargs=None,
                 return_values: Optional[List[Any]] = None,
                 call_fake: Optional[Callable] = None):
        self.return_values = return_values if return_values is not None else []
        self.call_fake = call_fake
        if call_fake is not None and not callable(call_fake):
            raise Exception("Setup.call_fake must be function")
        self.args = args
        if args is not None and type(args) != list:
            raise Exception("Setup.args must be an array")
        self.kwargs = kwargs
        if kwargs is not None and type(kwargs) != dict:
            raise Exception("Setup.kwargs must be an dictionary")
        self.calls = []

    def call_at(self, index):
        if index <= len(self.calls) - 1:
            return self.calls[index]
        else:
            raise Exception("No call at index {}. Call count is {}".format(index, len(self.calls)))

    def __str__(self):
        return "\n\targs: {}, \n\tkwargs: {}, \n\treturn_values: {}".format(self.args, self.kwargs, self.return_values)

    def append_call(self, call_args):
        self.calls.append(call_args)

    def expected_to_have_been_called(self, with_args=None, with_kwargs=None,
                                     times=None, exactly_times=None, negate: bool = False):
        match_count = 0
        for call in self.calls:
            match = True
            call_args = call['args']
            call_kwargs = call['kwargs']
            setup_args = with_args
            setup_kwargs = with_kwargs

            if setup_args is not None and len(setup_args) > 0:
                if len(setup_args) != len(call_args):
                    match = False
                if match:
                    for idx, arg in enumerate(call_args):
                        if not _args_match(arg, setup_args[idx]):
                            match = False
                            break

            if setup_kwargs is not None and len(setup_kwargs.keys()) > 0:
                if len(setup_kwargs.keys()) != len(call_kwargs.keys()):
                    match = False
                if match:
                    for key, value in setup_kwargs.items():
                        if not (key in setup_kwargs and _args_match(value, setup_kwargs[key])):
                            match = False
                            break
            if match:
                match_count += 1

        _assert_call_count({'args': with_args, 'kwargs': with_kwargs}, self.calls,
                           match_count, times, exactly_times, negate)

    def expected_not_to_have_been_called(self, args=None, kwargs=None, times=None, exactly_times=None):
        self.expected_to_have_been_called(args, kwargs, times, exactly_times, negate=True)


class MockSetup:
    mock_history = {}

    @staticmethod
    def mock_name(mock):
        return re.search(r'<.*Mock name=\'([a-zA-Z0-9._()-]+)\'', str(mock), re.IGNORECASE).group(1)

    @staticmethod
    def new_mock(
            name: str,
            args=None,
            kwargs=None,
            return_values: Optional[List[Any]] = None,
            call_fake: Optional[Callable] = None):

        mock = Mock(name=name)
        MockSetup.mock_one(mock, args, kwargs, return_values, call_fake)
        return mock

    @staticmethod
    def mock_one(mock,
                 args=None,
                 kwargs=None,
                 return_values: Optional[List[Any]] = None,
                 call_fake: Optional[Callable] = None,
                 reset: bool = False):
        setup = Setup(args, kwargs, return_values, call_fake)
        if reset:
            MockSetup.reset(mock)
        MockSetup.mock(mock, setups=[setup])

    @staticmethod
    def setup(mock, index: int) -> Setup:
        return MockSetup.mock_history[id(mock)][index]

    @staticmethod
    def setups(mock) -> List[Setup]:
        return MockSetup.mock_history[id(mock)]

    @staticmethod
    def reset(mock):
        MockSetup.mock_history[id(mock)] = []

    @staticmethod
    def mock(mock, setups: List[Setup]):
        setup_return_history = {}

        if id(mock) not in MockSetup.mock_history:
            MockSetup.mock_history[id(mock)] = []

        MockSetup.mock_history[id(mock)] = setups+MockSetup.mock_history[id(mock)]
        mock.setup = lambda index: MockSetup.mock_history[id(mock)][0]

        def side_effect(*args, **kwargs):
            setups = MockSetup.mock_history[id(mock)]

            for cur_setup in setups:
                setup: Setup = cur_setup
                match = True
                setup_args = setup.args
                setup_kwargs = setup.kwargs
                call_fake = setup.call_fake

                if setup_args is not None and len(setup_args) > 0:
                    if len(args) != len(setup_args):
                        match = False
                    if match:
                        for idx, arg in enumerate(args):
                            if not _args_match(arg, setup_args[idx]):
                                match = False
                                break

                if setup_kwargs is not None and len(setup_kwargs.keys()) > 0:
                    if len(setup_kwargs.keys()) != len(kwargs.keys()):
                        match = False
                    if match:
                        for key, value in kwargs.items():
                            if not (key in setup_kwargs and _args_match(value, setup_kwargs[key])):
                                match = False
                                break

                if match:
                    if call_fake is not None:
                        return_value = call_fake({'args': args, 'kwargs': kwargs})
                    else:
                        if len(setup.return_values) == 0:
                            raise Exception("Setup return values cannot be empty: {}".format(setup))

                        return_index = setup_return_history[id(setup)] \
                            if id(setup) in setup_return_history \
                            else 0
                        if return_index < len(setup.return_values):
                            setup_return_history[id(setup)] = return_index + 1
                            return_value = setup.return_values[return_index]
                        else:
                            return_value = setup.return_values[-1]

                        setup.append_call(dict(method=MockSetup.mock_name(mock), args=list(args), kwargs=kwargs))

                        if type(return_value) is RaiseException:
                            raise_exception: RaiseException = return_value
                            raise raise_exception.exception

                    return return_value

            error_message = \
                "NO MATCH FOUND for method {} with \n\targs:{}, \n\tkwargs:{}, \nMethod setups were:\n {}" \
                    .format(mock, list(args), kwargs, "\n".join(list(map(str, setups))))
            print(error_message)
            raise Exception("NO MATCH FOUND: See above for details")

        mock.side_effect = side_effect
        return mock

    @staticmethod
    def match_dict(dict1):
        return {'__match__': dict1}

    @staticmethod
    def any():
        return {'__match__': '<Any>'}

    @staticmethod
    def match(func: Callable[[Any], bool]):
        return {'__match__': func}


def _args_match(arg, setup_arg):
    if type(setup_arg) == dict and '__match__' in setup_arg:
        match_info = setup_arg['__match__']
        if type(match_info) == str and match_info == '<Any>':
            return True
        if type(match_info) == dict:
            same, _ = same_dict(arg, match_info)
            return same
        if callable(match_info):
            func: Callable[[Any], bool] = match_info
            return func(arg)
    else:
        return arg == setup_arg


def _assert_call_count(call, calls,
                       call_count: int, times: Optional[int] = None,
                       exactly_times: Optional[int] = None, negate: bool = False):
    times = times if times is not None else 1
    exactly_text = 'exactly' if exactly_times is not None else ''
    negate_text = 'not have been' if negate else ''
    bool_exp = call_count == times if exactly_times is not None else call_count >= times

    if negate:
        bool_exp = not bool_exp

    expected_call_text = _print_call(call['args'], call['kwargs'])

    assert bool_exp, "Expected to {} be called {} {} times. But call count was: {}. " \
                     "\n\nExpected call:\n{}" \
                     "\n\nActual calls:\n{}" \
        .format(negate_text, exactly_text, times, call_count, expected_call_text,
                '\n'.join(list(map(lambda x: ''.join(ndiff(expected_call_text.splitlines(True),
                                                           _print_call(x['args'], x['kwargs']).splitlines(True))), calls))))


def _print_call(args: List[Any], kwargs: dict):
    if kwargs is None:
        kwargs = {}
    if args is None:
        args = []

    def _print_val(d):
        if type(d) == list:
            print_arg = lambda x: '\t{}: {}'.format(x[0], _print_val(x[1]))
            return '\n'.join(list(map(print_arg, enumerate(list(args)))))
        if type(d) == str:
            return d.replace('\n', '\n\t   ')
        if type(d) == dict:
            return '\n\t   '.join(list(map(lambda x: '{}: {}'.format(x[0], _print_val(x[1])), d.items())))
        if type(d) == tuple:
            return _print_val(list(d))
        return '\n\t   {}'.format(d)

    return '\nargs:{}\nkwargs:{}'.format(_print_val(args), _print_val(kwargs))
