from typing import Callable, Any
import krogon.either as E


class Step:
    def __init__(self, name: str):
        self.name = name


class GenericStep(Step):
    def __init__(self, name: str, func: Callable[[], E.Either[Any, Any]]):
        super().__init__(name=name)
        self.func = func

    def exec(self):
        return self.func()


def step(name: str, func: Callable[[], E.Either[Any, Any]]):
    return GenericStep(name, func)
