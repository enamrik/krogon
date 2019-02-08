from typing import List, Any, Optional
import krogon.maybe as M


def nlist(items: Optional[List[Any]]):
    return NullableList(items)


def nmap(map: dict):
    return NullableMap(map)


def dict_get_or_none(a_dict: dict, key: Any):
    return a_dict[key] if a_dict is not None and key in a_dict else None


class NullableList(list):
    def append_if_value(self, value: M.Maybe):
        return value | M.from_maybe | dict(if_just=lambda val: NullableList(self + [val]),
                                           if_nothing=lambda: self)

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
