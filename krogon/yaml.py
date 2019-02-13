from ruamel.yaml import YAML
from ruamel.yaml.compat import StringIO


def dump(obj: dict, default_flow_style=False) -> str:
    yaml = YAML()
    yaml.default_flow_style = default_flow_style
    stream = StringIO()
    yaml.dump(obj, stream)
    return stream.getvalue()


def load(obj_str: str) -> dict:
    yaml = YAML()
    return yaml.load(obj_str)


