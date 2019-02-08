from dictdiffer import diff


def assert_same_dict(dict1, dict2):
    result = list(diff(dict1, dict2))
    assert len(result) == 0, "Should be the same. Instead got diff: {}".format(result)

