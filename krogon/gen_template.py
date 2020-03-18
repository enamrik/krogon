import sys
from typing import List
from krogon.config import config, Config
from krogon.k8s.eval_template import eval_template
from krogon.k8s.kubectl import noop_conn
from krogon.k8s.template_context import TemplateContext
from krogon.pipeline import pipeline
import krogon.yaml as y
import krogon.either as E


def gen_template(templates: List):
    conf = config()
    k_ctl = noop_conn()(conf)
    t_ctx = TemplateContext(conf, k_ctl)
    file_path = '{}/k8s.yaml'.format(conf.output_dir)
    conf.fs.delete(file_path)

    return pipeline(templates, lambda template, cur_ctx: _plan_template(conf, template, cur_ctx, file_path), t_ctx) \
           | E.on | dict(success=lambda _: conf.log.info('Writing k8s template to {}'.format(file_path))) \
           | E.on | dict(success=lambda _: conf.log.info('DONE'),
                         failure=lambda e: conf.log.error('FAILED: {}'.format(e))) \
           | E.on | dict(failure=lambda e: sys.exit(1))


def _plan_template(conf: Config, template, cur_ctx: TemplateContext, file_path: str):
    cur_ctx = TemplateContext.new_from_state(cur_ctx)
    eval_template(template, cur_ctx, conf.log)
    _write_template_to_disk(cur_ctx.templates, file_path, conf)
    return E.success(cur_ctx)


def _write_template_to_disk(templates: List[dict], file_path: str, conf: Config):
    templates_out = y.load_all(conf.fs.read(file_path)) if conf.fs.exists(file_path) else []
    templates_out = templates_out + templates
    conf.fs.write(file_path, y.combine_templates(templates_out))
