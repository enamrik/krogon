from typing import Callable, TypeVar, Tuple, Union
from krogon.infix import Infix
import traceback

A = TypeVar('A')
Ap = TypeVar('Ap')
E = TypeVar('E')
Ep = TypeVar('Ep')


Either = Union[Tuple['success', A], Tuple['failure', E]]


def success(value=None):
    return "success", value


def failure(error):
    return "failure", error


@Infix
def then(either: Either[A, E], func: Callable[[A], Either[Ap, E]]) -> Either[Ap, E]:
    if either[0] == "success":
        return _cast_to_either(func(either[1]))
    elif either[0] == "failure":
        return either
    else:
        raise Exception('Invalid Either: {}'.format(either))


@Infix
def map(either: Either[A, E], mapper: Callable[[A], Ap]) -> Either[Ap, E]:
    if either[0] == "success":
        return "success", mapper(either[1])
    elif either[0] == "failure":
        return either
    else:
        raise Exception('Invalid Either: {}'.format(either))


@Infix
def on(either: Either[A, E], dict_args: dict) -> Either[A, E]:
    success_f: Callable = dict_args['success'] if 'success' in dict_args else (lambda _: {})
    failure_f: Callable = dict_args['failure'] if 'failure' in dict_args else (lambda _: {})
    whatever_f: Callable = dict_args['whatever'] if 'whatever' in dict_args else (lambda _v, _e: {})

    if either[0] == "success":
        success_f(either[1])
        whatever_f(either[1], None)
    elif either[0] == "failure":
        failure_f(either[1])
        whatever_f(None, either[1])
    else:
        raise Exception('Invalid Either: {}'.format(either))

    return either


@Infix
def map_error(either: Either[A, E], mapper: Callable[[E], Ep]) -> Either[A, Ep]:
    if either[0] == "success":
        return either
    elif either[0] == "failure":
        return "failure", mapper(either[1])
    else:
        raise Exception('Invalid Either: {}'.format(either))


@Infix
def catch_error(either: Either[A, E], func: Callable[[E], Either[Ap, Ep]]) -> Either[Ap, Ep]:
    if either[0] == "success":
        return either
    elif either[0] == "failure":
        return _cast_to_either(func(either[1]))
    else:
        raise Exception('Invalid Either: {}'.format(either))


@Infix
def from_either(either: Either[A, E], dict_args) -> Ap:
    if_success: Callable = dict_args['if_success']
    if_failure: Callable = dict_args['if_failure']

    if either[0] == "success" and if_success is not None:
        return if_success(either[1])
    elif either[0] == "failure" and if_failure is not None:
        return if_failure(either[1])


class TryCatchError(Exception):
    def __init__(self, error, trace):
        self.caught_error = error
        self.trace = trace


def try_catch(func: Callable):
    try:
        return _cast_to_either(func())
    except Exception as error:
        return "failure", TryCatchError(error, traceback.format_exc())


def _cast_to_either(result):
    if isinstance(result, tuple) and len(result) == 2:
        either_type, value = result
        if either_type == "success" or either_type == "failure":
            return result
    return "success", result


