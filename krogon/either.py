from typing import Callable, TypeVar, Generic
from krogon.infix import Infix
import traceback

A = TypeVar('A')
Ap = TypeVar('Ap')
E = TypeVar('E')
Ep = TypeVar('Ep')


class Either(Generic[A, E]):
    pass


class Success(Either, Generic[A, E]):

    def __init__(self, value: A = None):
        self.value = value

    def __eq__(self, other: Either) -> bool:
        return isinstance(other, Success) and self.value == other.value

    def __str__(self) -> str:
        return "Success{{ {} }}".format(self.value)


class Failure(Either, Generic[A, E]):

    def __init__(self, value: E):
        self.value = value

    def __eq__(self, other: Either) -> bool:
        return isinstance(other, Failure) and self.value == other.value

    def __str__(self) -> str:
        return "Failure{{ {} }}".format(self.value)


@Infix
def then(either: Either[A, E], func: Callable[[A], Either[Ap, E]]) -> Either[Ap, E]:
    if type(either) is Success:
        success: Success = either
        result = func(success.value)
        if isinstance(result, Either):
            return result
        else:
            return Success(result)
    elif type(either) is Failure:
        return either
    else:
        raise Exception('Invalid Either: {}'.format(either))


@Infix
def map(either: Either[A, E], mapper: Callable[[A], Ap]) -> Either[Ap, E]:
    if type(either) is Success:
        right: Success = either
        return Success(mapper(right.value))
    elif type(either) is Failure:
        return either
    else:
        raise Exception('Invalid Either: {}'.format(either))


@Infix
def on(either: Either[A, E], dict_args: dict) -> Either[A, E]:
    success: Callable = dict_args['success'] if 'success' in dict_args else (lambda _: {})
    failure: Callable = dict_args['failure'] if 'failure' in dict_args else (lambda _: {})
    whatever: Callable = dict_args['whatever'] if 'whatever' in dict_args else (lambda: {})

    if type(either) is Success:
        success_either: Success = either
        success(success_either.value)
        whatever()
    elif type(either) is Failure:
        failure_either: Failure = either
        failure(failure_either.value)
        whatever()
    elif not isinstance(either, Either):
        raise Exception('Invalid Either: {}, args: {}'.format(either, dict_args))

    return either


@Infix
def map_error(either: Either[A, E], mapper: Callable[[E], Ep]) -> Either[A, Ep]:
    if type(either) is Success:
        return either
    elif type(either) is Failure:
        failure: Failure = either
        return Failure(mapper(failure.value))
    else:
        raise Exception('Invalid Either: {}'.format(either))


@Infix
def catch_error(either: Either[A, E], func: Callable[[E], Either[Ap, Ep]]) -> Either[Ap, Ep]:
    if type(either) is Success:
        return either
    elif type(either) is Failure:
        failure: Failure = either
        result = func(failure.value)
        if isinstance(result, Either):
            return result
        else:
            return Success(result)
    else:
        raise Exception('Invalid Either: {}'.format(either))


@Infix
def from_either(either: Either[A, E], dict_args) -> Ap:
    if_success: Callable = dict_args['if_success']
    if_failure: Callable = dict_args['if_failure']

    if type(either) is Success and if_success is not None:
        success_either: Success = either
        return if_success(success_either.value)
    elif type(either) is Failure and if_failure is not None:
        failure_either: Failure = either
        return if_failure(failure_either.value)


class TryCatchError(Exception):
    def __init__(self, error, trace):
        self.caught_error = error
        self.trace = trace


def try_catch(func: Callable):
    try:
        result = func()
        return result if isinstance(result, Either) else Success(result)
    except Exception as error:
        return Failure(TryCatchError(error, traceback.format_exc()))
