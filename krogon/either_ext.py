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
