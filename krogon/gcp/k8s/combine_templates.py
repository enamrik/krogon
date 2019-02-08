from typing import List, Any
import krogon.yaml as yaml


def combine_templates(templates: List[dict]) -> str:
    template_strings = list(map(lambda template: yaml.dump(template), templates))
    return '\n---\n'.join(template_strings)

