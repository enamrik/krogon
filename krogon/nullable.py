from typing import List, Any, Optional
import krogon.maybe as M


def nlist(items=None):
    if items is None:
        items = []
    return NullableList(items)


def nmap(map: dict):
    return NullableMap(map)


def dict_get_or_none(a_dict: dict, key: Any):
    return a_dict[key] if a_dict is not None and key in a_dict else None


class NullableList(list):
    def append_if_value(self, value: M.Maybe[Any]):
        return value | M.from_maybe | dict(if_just=lambda val: NullableList(self + [val]),
                                           if_nothing=lambda: self)

    def append_if_list(self, value: M.Maybe[list]):
        return value | M.from_maybe | dict(if_just=lambda list: NullableList(self + list),
                                           if_nothing=lambda: self)

    def append(self, value: Any):
        return NullableList(self + [value])

    def to_list(self):
        return list(self)


class NullableMap(dict):
    def get_or_none(self, key: Any):
        return self[key] if key in self else None

    def append_if_value(self, key: Any, value: M.Maybe):
        return value | M.from_maybe | dict(if_just=lambda val: NullableMap(dict(self, **{key: val})),
                                           if_nothing=lambda: self)

    def to_map(self):
        return dict(self)
