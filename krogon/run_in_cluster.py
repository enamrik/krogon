import sys
from typing import List, Callable
from krogon.config import config, Config
from krogon.either_ext import chain
from krogon.k8s.eval_template import eval_template
from krogon.k8s.kubectl import KubeCtl, discover_conn
from krogon.k8s.template_context import TemplateContext
from krogon.pipeline import pipeline
import krogon.yaml as y
import krogon.either as E


def run_in_cluster(templates: List, conn: Callable[[Config], KubeCtl] = None):
    conf = config()

    if conn is None:
        conn = discover_conn()

    k_ctl = conn(conf)
    t_ctx = TemplateContext(conf, k_ctl)

    conf.log.info("KROGON:")
    conf.log.info("version: {}".format(conf.krogon_version))
    conf.log.info("deleting: {}".format(conf.deleting))
    conf.log.info("template_output: {}".format(conf.output_template))
    conf.log.info('Kubectl conn: {}'.format(k_ctl))

    return _run_in_cluster(conf, templates, t_ctx, k_ctl) \
           | E.on | dict(success=lambda _: conf.log.info('DONE'),
                         failure=lambda e: conf.log.error('FAILED: {}'.format(e))) \
           | E.on | dict(failure=lambda e: sys.exit(1))


def _run_in_cluster(conf: Config, templates, t_ctx: TemplateContext, k_ctl: KubeCtl):
    if conf.deleting:
        return _in_clusters(k_ctl, lambda cluster_name: _exec_templates(cluster_name, templates, conf, t_ctx, k_ctl))
    elif conf.output_template:
        return _in_clusters(k_ctl, lambda cluster_name: _plan_templates(cluster_name, templates, conf, t_ctx))
    else:
        return _in_clusters(k_ctl, lambda cluster_name: _exec_templates(cluster_name, templates, conf, t_ctx, k_ctl))


def _exec_templates(cluster_name: str, templates: List, conf: Config, t_ctx: TemplateContext, k_ctl: KubeCtl):

    return pipeline(templates,
                    lambda template, cur_ctx:
                        k_ctl.apply(_gen_template(template, cluster_name, conf, cur_ctx), cluster_name)
                        | E.then | (lambda _: cur_ctx),
                    t_ctx)


def _delete_templates(cluster_name: str, templates: List, conf: Config, t_ctx: TemplateContext, k_ctl: KubeCtl):

    return pipeline(templates,
                    lambda template, cur_ctx:
                        k_ctl.delete(_gen_template(template, cluster_name, conf, cur_ctx), cluster_name)
                        | E.then | (lambda _: cur_ctx),
                    t_ctx)


def _plan_templates(cluster_name: str, templates, conf: Config, t_ctx: TemplateContext):
    cluster_dir = '{}/{}'.format(conf.output_dir, cluster_name)
    conf.fs.ensure_path(cluster_dir)
    file_path = '{}/k8s.yaml'.format(cluster_dir)
    conf.fs.delete(file_path)

    return pipeline(templates, lambda template, cur_ctx: _write_template_plan(cluster_name, conf, file_path, template, cur_ctx), t_ctx) \
           | E.on | dict(success=lambda _: conf.log.info('Writing k8s template to {}'.format(file_path)))


def _write_template_plan(cluster_name, conf, file_path, template: str, cur_ctx: TemplateContext):
    template_outs = _gen_template(template, cluster_name, conf, cur_ctx)

    templates_out = y.load_all(conf.fs.read(file_path)) if conf.fs.exists(file_path) else []
    templates_out = templates_out + template_outs
    conf.fs.write(file_path, y.combine_templates(templates_out))

    return E.success(cur_ctx)


def _gen_template(template, cluster_name: str, conf: Config, cur_ctx: TemplateContext) -> List[dict]:
    cur_ctx = TemplateContext.new_from_state(cur_ctx)
    cur_ctx.set_state('cluster_name', cluster_name)
    eval_template(template, cur_ctx, conf.log)
    return cur_ctx.templates


def _in_clusters(k_ctl: KubeCtl, action):
    return k_ctl.get_clusters() \
           | E.then | (lambda cluster_names: chain(cluster_names, lambda cluster_name: action(cluster_name)))

