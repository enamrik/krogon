from typing import Any, Callable, Optional, List
import python_either.either as E


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