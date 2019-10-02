from typing import List, Union
from krogon.pipeline import pipeline
from krogon.either_ext import chain
import krogon.yaml as y
import krogon.either as E
import krogon.k8s.kubectl as k
from krogon.exec_context import ExecContext
from krogon.steps.k8s.run_template import exec_template, build_template


def run_in_cluster(named: Union[str, List[str]], templates: List):

    cluster_tags = named \
        if isinstance(named, list) \
        else [named]

    return dict(
        exec=lambda c: _run(c, list(templates), cluster_tags),
        delete=lambda c: _delete(c, list(templates), cluster_tags)
    )


def _delete(context: ExecContext, steps: List, cluster_tags: List[str]):
    steps.reverse()

    def _delete_in_cluster(cluster_name):
        return pipeline(steps, lambda step, cur_ctx: exec_template(step, cur_ctx, cluster_name), context)

    def _delete_in_clusters(cluster_names: List[str]):
        return chain(cluster_names, lambda cluster_name: _delete_in_cluster(cluster_name))

    return \
        k.get_clusters(context.kubectl, by_tags=cluster_tags) \
        | E.then | (lambda cluster_names: _delete_in_clusters(cluster_names))


def _run(context: ExecContext, steps: List, cluster_tags: List[str]):

    def _run_in_cluster(cluster_name):
        run_context = context.copy()
        run_context.set_state('cluster_name', cluster_name)
        run_context.set_state('cluster_tags', cluster_tags)
        return pipeline(steps,
                        lambda step, cur_ctx:
                            build_template(step, cur_ctx)
                            if context.config.output_template
                            else exec_template(step, cur_ctx, cluster_name),
                        run_context) \
               | E.then | (lambda cur_ctx: _handle_result(context=cur_ctx,
                                                          cluster_name=cluster_name))

    def _exec_in_clusters(cluster_names: List[str]):
        return chain(cluster_names, lambda cluster_name: _run_in_cluster(cluster_name))

    return \
        k.get_clusters(context.kubectl, by_tags=cluster_tags) \
        | E.then | (lambda cluster_names: _exec_in_clusters(cluster_names))


def _handle_result(context: ExecContext, cluster_name):
    if context.config.output_template:
        combined_template = y.combine_templates(context.templates)

        file_dir = '{}/{}'.format(context.config.output_dir, cluster_name)
        context.fs.ensure_path(file_dir)
        file_path = '{}/k8s.yaml'.format(file_dir)

        context.logger.info('Writing k8s template to {}'.format(file_path))

        context.fs.write(file_path, combined_template)
        return E.success(combined_template)
    else:
        return E.success()
