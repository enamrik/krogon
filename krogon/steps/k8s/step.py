from typing import List
from krogon.pipeline import pipeline
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
    return pipeline(steps, lambda step, cur_ctx: _run_template(step, cur_ctx), context) \
           | E.then | (lambda cur_ctx: _handle_delete(context=cur_ctx,
                                                      cluster_name=cluster_name))


def _run(context: ExecContext, steps: List, cluster_name: str):
    return pipeline(steps, lambda step, cur_ctx: _run_template(step, cur_ctx), context) \
           | E.then | (lambda cur_ctx: _handle_result(context=cur_ctx,
                                                      cluster_name=cluster_name))


def _run_template(template, context: ExecContext):
    if hasattr(template, 'run'):
        template_dicts = template.run()
        context.templates = context.templates + template_dicts
        return context

    if hasattr(template, 'map_context'):
        return template.map_context(context)

    return "failure", "Unsupported template type: {}".format(type(template))


def _handle_result(context: ExecContext, cluster_name):
    if context.config.output_template:
        combined_template = y.combine_templates(context.templates)
        file_path = '{}/k8s.yaml'.format(context.config.output_dir)
        context.logger.info('Writing k8s template to {}'.format(file_path))
        context.fs.write(file_path, combined_template)
        return E.success(combined_template)
    else:
        return k.apply(context.kubectl, context.templates, cluster_name)


def _handle_delete(context: ExecContext, cluster_name):
    return k.delete(context.kubectl, context.templates, cluster_name)
