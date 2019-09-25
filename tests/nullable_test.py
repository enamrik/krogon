from krogon.nullable import nlist, nmap
import krogon.maybe as M


def test_will_append_to_list_if_value():
    assert nlist([1]).append_if_value(M.just(2)) == [1, 2]


def test_will_ignore_append_list_if_nothing():
    assert nlist([1]).append_if_value(M.nothing()) == [1]


def test_will_concat_list_if_value():
    assert nlist([1, 2]).append_if_list(M.just([3, 4])) == [1, 2, 3, 4]


def test_will_ignore_list_if_nothing():
    assert nlist([1, 2]).append_if_list(M.nothing()) == [1, 2]


def test_will_append_item():
    assert nlist([1, 2]).append(3) == [1, 2, 3]


def test_can_convert_to_base_list_type():
    a_list = nlist([1, 2]).to_list()
    assert a_list == [1, 2]
    assert type(a_list) == list


def test_will_append_to_map_if_value():
    assert nmap({'a': 1}).append_if_value('b', M.just(2)) == {'a': 1, 'b': 2}


def test_will_ignore_append_to_map_if_nothing():
    assert nmap({'a': 1}).append_if_value('b', M.nothing()) == {'a': 1}


def test_will_get_none_if_key_missing():
    assert nmap({'a': 1}).get_or_none('b') is None


def test_will_get_value_if_key_present():
    assert nmap({'a': 1}).get_or_none('a') == 1


def test_can_convert_to_base_map_type():
    a_map = nmap({'a': 1}).to_map()
    assert a_map == {'a': 1}
    assert type(a_map) == dict


