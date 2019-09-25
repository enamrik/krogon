import krogon.maybe as M


def test_can_make_just_maybe():
    assert M.just(1) == ("just", 1)


def test_can_make_nothing_maybe():
    assert M.nothing() == ("nothing", None)


def test_can_map_just_maybe():
    assert M.just(1) | M.map | (lambda x: x + 1) == M.just(2)


def test_can_map_nothing_maybe():
    assert M.nothing() | M.map | (lambda x: x + 1) == M.nothing()


def test_can_chain_just_maybe():
    assert M.just(1) | M.then | (lambda x: M.just(x + 1)) == M.just(2)


def test_can_chain_just_maybe_and_wrap_non_maybe_result():
    assert M.just(1) | M.then | (lambda x: x + 1) == M.just(2)


def test_can_chain_maybe():
    assert M.just(1) | M.then | (lambda _: M.nothing()) == M.nothing()


def test_can_catch_nothing_and_return_just_value():
    assert M.nothing() | M.catch_nothing | (lambda: M.just(1)) == M.just(1)


def test_can_catch_nothing_and_return_value():
    assert M.nothing() | M.catch_nothing | (lambda: 1) == M.just(1)


def test_can_ignore_catch_nothing_if_value():
    assert M.just(2) | M.catch_nothing | (lambda: 1) == M.just(2)


def test_from_maybe_can_return_on_value():
    assert M.just(1) \
           | M.from_maybe | dict(
        if_just=lambda x: x + 1,
        if_nothing=lambda: "nothing") == 2


def test_from_maybe_can_return_on_nothing():
    assert M.nothing() \
           | M.from_maybe | dict(
        if_just=lambda _: None,
        if_nothing=lambda: "defaultValue") == "defaultValue"

