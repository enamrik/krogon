from typing import Callable, TypeVar, Generic
from krogon.infix import Infix

A = TypeVar('A')
B = TypeVar('B')
E = TypeVar('E')


class Maybe(Generic[A]):
    pass


class Just(Maybe, Generic[A]):

    def __init__(self, value: A) -> None:
        self.value = value

    def __eq__(self, other: Maybe[A]) -> bool:
        return isinstance(other, Just) and self.value == other.value

    def __str__(self) -> str:
        return "Just %s" % self.value


class Nothing(Maybe, Generic[A]):

    def __eq__(self, other: Maybe[A]) -> bool:
        return isinstance(other, Maybe)

    def __str__(self) -> str:
        return "Nothing"


@Infix
def then(maybe: Maybe[A], func: Callable[[A], Maybe[B]]) -> Maybe[B]:
    if type(maybe) is Just:
        just: Just = maybe
        return func(just.value)
    elif type(maybe) is Nothing:
        return maybe


@Infix
def map(maybe: Maybe[A], mapper: Callable[[A], B]) -> Maybe[B]:
    if type(maybe) is Just:
        just: Just = maybe
        return Just(mapper(just.value))
    elif type(maybe) is Nothing:
        return maybe


@Infix
def value_or_default(maybe: Maybe[A], value: Callable[[A], B], default_value: B):
    return maybe | from_maybe | (dict(if_just=value, if_nothing=lambda: default_value))


@Infix
def from_maybe(maybe: Maybe[A], dict_args: dict) -> B:
    if_just: Callable = dict_args['if_just']
    if_nothing: Callable = dict_args['if_nothing']

    if type(maybe) is Just and if_just is not None:
        just_maybe: Just = maybe
        return if_just(just_maybe.value)
    elif type(maybe) is Nothing and if_nothing is not None:
        return if_nothing()
    else:
        raise Exception('Invalid Maybe: {}, {}'.format(maybe, dict_args))
