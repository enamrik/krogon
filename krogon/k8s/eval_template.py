import sys

from krogon.k8s.template_context import TemplateContext
from krogon.logger import Logger


def eval_template(template, context: TemplateContext, logger: Logger):
    logger.info("Running template: {}".format(template))

    if hasattr(template, 'run'):
        template_dicts = template.run()
        context.append_templates(template_dicts)
    elif hasattr(template, 'map_context'):
        template.map_context(context)
    else:
        sys.exit("Unsupported template type: {}".format(type(template)))
