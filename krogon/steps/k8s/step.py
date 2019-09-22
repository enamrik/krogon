from typing import List
from python_either.either_ext import chain
import krogon.yaml as y
import python_either.either as E
import krogon.k8s.kubectl as k
from krogon.exec_context import ExecContext


def run_in_cluster(named: str, templates: List):
    cluster_name = named
    return dict(
        exec=lambda c: _run(c, list(templates), cluster_name),
        delete=lambda c: _delete(c, list(templates), cluster_name)
    )


def _delete(context: ExecContext, steps: List, cluster_name: str):
    return chain(steps, lambda step: _gen_template_string(step, context)) \
           | E.then | (lambda x: _handle_delete(templates=x,
                                                context=context,
                                                cluster_name=cluster_name))


def _run(context: ExecContext, steps: List, cluster_name: str):
    return chain(steps, lambda step: _gen_template_string(step, context)) \
           | E.then | (lambda x: _handle_result(templates=x,
                                                context=context,
                                                cluster_name=cluster_name))


def _gen_template_string(template, context: ExecContext):
    if hasattr(template, 'to_string'):
        return template.to_string(context)

    return "failure", "Unsupported template type: {}".format(type(template))


def _handle_result(templates: List[str], context: ExecContext, cluster_name):
    if context.config.output_template:
        combined_template = y.combine_templates(templates)
        file_path = '{}/k8s.yaml'.format(context.config.output_dir)
        context.logger.info('Writing k8s template to {}'.format(file_path))
        context.fs.write(file_path, combined_template)
        return E.success(combined_template)
    else:
        return k.apply(context.kubectl, templates, cluster_name)


def _handle_delete(templates: List[str], context: ExecContext, cluster_name):
    return k.delete(context.kubectl, templates, cluster_name)
