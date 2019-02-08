import krogon.either as E
from typing import Callable, List, Any, Optional
from krogon.either import Either


def chain(items: List[Any], processor: Callable[[Any], Either[Any, Any]]) -> Either[Any, Any]:
    def chain_func(remaining_items: List[Any],
                   resulting_items: List[Any]) -> Either[Any, Any]:

        if len(remaining_items) == 0:
            return E.Success(resulting_items)

        item = remaining_items[0]
        new_remaining_items = remaining_items[1:]

        return E.try_catch(lambda: processor(item)) \
               | E.then | (lambda result: chain_func(new_remaining_items, resulting_items+[result]))

    return chain_func(remaining_items=items, resulting_items=[])


def pipeline(funcs: List[Callable[[Any], Any]], initial_result: Optional[Any] = None) -> Either:
    def chain_func(remaining_funcs: List[Callable[[List[Any]], Any]],
                   last_result: Optional[Any]) -> Either:

        if len(remaining_funcs) == 0:
            return E.Success(last_result)

        func = remaining_funcs[0]
        remaining_funcs = remaining_funcs[1:]

        return E.try_catch(lambda: func(last_result)) \
               | E.then | (lambda next_result: chain_func(remaining_funcs, next_result))

    return chain_func(funcs, initial_result)
