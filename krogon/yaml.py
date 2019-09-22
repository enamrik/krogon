from typing import List, Union
from ruamel.yaml import YAML
from ruamel.yaml.compat import StringIO


def combine_templates(templates: List[Union[dict, str]]) -> str:
    def _get_template_string(template: Union[dict, str]) -> str:
        if type(template) == dict:
            template = dump(template)
        return template

    template_strings = list(map(_get_template_string, templates))
    return '\n---\n'.join(template_strings)


def dump(obj: dict, default_flow_style=False) -> str:
    yaml = YAML()
    yaml.default_flow_style = default_flow_style
    stream = StringIO()
    yaml.dump(obj, stream)
    return stream.getvalue()


def load_all(template_str: str) -> List[dict]:
    templates_str = template_str.split('---')
    return list(map(lambda x: load(x), templates_str))


def load(obj_str: str) -> dict:
    yaml = YAML()
    return yaml.load(obj_str)





