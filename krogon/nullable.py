from typing import Any, List
import krogon.maybe as M


def nlist(items=None):
    if items is None:
        items = []
    return NullableList(items)


def nmap(map: dict):
    return NullableMap(map)


class NullableList(list):
    def append_if_value(self, value: M.Maybe[Any]):
        return value | M.from_maybe | dict(if_just=lambda val: NullableList(self + [val]),
                                           if_nothing=lambda: self)

    def append_if_list(self, value: M.Maybe[list]):
        return value | M.from_maybe | dict(if_just=lambda list: NullableList(self + list),
                                           if_nothing=lambda: self)

    def append(self, value: Any):
        return NullableList(self + [value])

    def append_all(self, a_list: List[Any]):
        return NullableList(self + a_list)

    def to_list(self):
        return list(self)


class NullableMap(dict):
    def get_or_none(self, key: Any):
        return self[key] if key in self else None

    def append_if_value(self, key: Any, value: M.Maybe):
        if value is None:
            return self

        return M.from_value(value) | M.from_maybe | dict(if_just=lambda val: NullableMap(dict(self, **{key: val})),
                                                         if_nothing=lambda: self)

    def to_maybe(self):
        if len(self.keys()) == 0:
            return M.nothing()
        else:
            return M.just(self.to_map())

    def to_map(self):
        return dict(self)
