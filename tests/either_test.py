import krogon.either as E


def test_can_make_success_either():
    assert E.success(1) == ("success", 1)


def test_can_make_empty_success_either():
    assert E.success() == ("success", None)


def test_can_make_failure_either():
    assert E.failure("someError") == ("failure", "someError")


def test_can_map_success_either():
    assert E.success(1) | E.map | (lambda x: x + 1) == E.success(2)


def test_can_map_failure_either():
    assert E.failure("someError") | E.map | (lambda x: x + 1) == E.failure("someError")


def test_can_chain_success_either():
    assert E.success(1) | E.then | (lambda x: E.success(x + 1)) == E.success(2)


def test_can_chain_success_either_and_wrap_non_either_result():
    assert E.success(1) | E.then | (lambda x: x + 1) == E.success(2)


def test_can_chain_success_either_and_fail():
    assert E.success(1) | E.then | (lambda _: E.failure("someError")) == E.failure("someError")


def test_can_map_error_and_ignore_success():
    assert E.success(1) | E.map_error | (lambda x: x + "Plus") == E.success(1)


def test_can_map_error():
    assert E.failure("someError") | E.map_error | (lambda x: x + "Plus") == E.failure("someErrorPlus")


def test_can_catch_error_and_return_error():
    assert E.failure("someError") | E.catch_error | (lambda x: E.failure(x + "Plus")) == E.failure("someErrorPlus")


def test_can_catch_error_and_return_success():
    assert E.failure("someError") | E.catch_error | (lambda x: E.success(1)) == E.success(1)


def test_can_catch_error_and_default_non_either_result_to_success():
    assert E.failure("someError") | E.catch_error | (lambda _: 1) == E.success(1)


def test_from_either_can_return_on_success():
    assert E.success(1) \
           | E.from_either | dict(
        if_success=lambda x: x + 1,
        if_failure=lambda _: "shouldSucceed") == 2


def test_from_either_can_return_on_failure():
    assert E.failure("someError") \
           | E.from_either | dict(
        if_success=lambda _: "shouldSucceed",
        if_failure=lambda e: e + "Plus") == "someErrorPlus"


on_success_value = None


def test_on_can_run_on_success():
    def _capture_value(x):
        global on_success_value
        on_success_value = x + 1

    E.success(1) | E.on | dict(success=_capture_value)
    assert on_success_value == 2


on_failure_value = None


def test_on_can_run_on_failure():
    def _capture_value(x):
        global on_failure_value
        on_failure_value = x + "Plus"

    E.failure("someError") | E.on | dict(failure=_capture_value)
    assert on_failure_value == "someErrorPlus"


on_whatever_value = None


def test_on_can_run_whatever_on_success():
    def _capture_value(value, _):
        global on_whatever_value
        on_whatever_value = value + 1

    E.success(1) | E.on | dict(whatever=_capture_value)
    assert on_whatever_value == 2


def test_on_can_run_whatever_on_failure():
    def _capture_value(_, error):
        global on_whatever_value
        on_whatever_value = error + "Plus"

    E.failure("someError") | E.on | dict(whatever=_capture_value)
    assert on_whatever_value == "someErrorPlus"
