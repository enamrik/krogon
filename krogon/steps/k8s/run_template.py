import krogon.k8s.kubectl as k
import krogon.either as E
import sys
from krogon.exec_context import ExecContext


def exec_template(template, context: ExecContext, cluster_name):
    context, template_dicts = _run_build_template(template, context)

    if len(template_dicts) > 0 and not context.config.output_template:
        action = k.delete \
            if context.config.deleting \
            else k.apply

        return action(context.kubectl, template_dicts, cluster_name) \
               | E.then | (lambda _: context)

    return context


def build_template(template, context: ExecContext):
    context, _ = _run_build_template(template, context)
    return context


def _run_build_template(template, context: ExecContext) -> E.Either:
    context.logger.info("Running template: {}".format(template))

    if hasattr(template, 'run'):
        template_dicts = template.run()
        context.append_templates(template_dicts)
        return context, template_dicts

    if hasattr(template, 'map_context'):
        template_count = len(context.templates)
        context = template.map_context(context)
        template_dicts = context.templates[template_count:len(context.templates)]
        return context, template_dicts

    return sys.exit("Unsupported template type: {}".format(type(template)))
