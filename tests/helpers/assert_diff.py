from dictdiffer import diff


def same_dict(dict1, dict2):
    result = list(diff(dict1, dict2))
    return len(result) == 0, result


def assert_same_dict(dict1, dict2):
    same, result = same_dict(dict1, dict2)
    assert same, "Should be the same. Instead got diff: {}".format(result)

