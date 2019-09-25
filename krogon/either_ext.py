import krogon.either as E
from typing import Callable, List, Any, Optional
from krogon.either import Either


def chain(items: List[Any], processor: Callable[[Any], Either[Any, Any]]) -> Either[Any, Any]:
    def chain_func(remaining_items: List[Any],
                   resulting_items: List[Any]) -> Either[Any, Any]:

        if len(remaining_items) == 0:
            return E.success(resulting_items)

        item = remaining_items[0]
        new_remaining_items = remaining_items[1:]

        return E.try_catch(lambda: processor(item)) \
               | E.then | (lambda result: chain_func(new_remaining_items, resulting_items+[result]))

    return chain_func(remaining_items=items, resulting_items=[])


def pipeline(items: Any,
             action: Callable[[Any, Any], Any],
             initial_result: Optional[Any] = None) -> E.Either:

    def chain_func(remaining_items: List[Any],
                   last_result: Optional[Any]) -> E.Either:

        if len(remaining_items) == 0:
            return E.success(last_result)

        item = remaining_items[0]
        remaining_items = remaining_items[1:]

        return E.try_catch(lambda: action(item, last_result)) \
               | E.then | (lambda next_result: chain_func(remaining_items, next_result))

    return chain_func(items, initial_result)
