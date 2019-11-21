from typing import List
import krogon.k8s.kubectl as k
import krogon.either as E
import sys
from krogon.exec_context import ExecContext


def exec_template(template_dicts: List[dict], context: ExecContext, cluster_name: str):

    if len(template_dicts) > 0:
        action = k.delete \
            if context.config.deleting \
            else k.apply

        return action(context.kubectl, template_dicts, cluster_name) \
               | E.then | (lambda _: context)

    return E.success(context)


class AddTemplateResult:
    def __init__(self, context: ExecContext, template_dicts: List[dict]):
        self.context = context
        self.template_dicts = template_dicts


def add_template_to_context(template, context: ExecContext) -> AddTemplateResult:
    context.logger.info("Running template: {}".format(template))

    if hasattr(template, 'run'):
        template_dicts = template.run()
        context.append_templates(template_dicts)
        return AddTemplateResult(context, template_dicts)

    if hasattr(template, 'map_context'):
        template_count = len(context.templates)
        context = template.map_context(context)
        template_dicts = context.templates[template_count:len(context.templates)]
        return AddTemplateResult(context, template_dicts)

    return sys.exit("Unsupported template type: {}".format(type(template)))
