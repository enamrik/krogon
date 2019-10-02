from typing import List
from krogon.pipeline import pipeline
import krogon.yaml as y
import krogon.either as E
from krogon.steps.k8s.run_template import build_template
from krogon.exec_context import ExecContext


def gen_template(templates: List):
    def _run_gen(context: ExecContext):
        return pipeline(templates, lambda step, cur_ctx: build_template(step, cur_ctx), context) \
               | E.then | (lambda cur_ctx: _handle_result(context=cur_ctx))

    return dict(
        exec=lambda c: _run_gen(c)
    )


def _handle_result(context: ExecContext):
    combined_template = y.combine_templates(context.templates)
    file_path = '{}/k8s.yaml'.format(context.config.output_dir)
    context.logger.info('Writing k8s template to {}'.format(file_path))
    context.fs.write(file_path, combined_template)
    return E.success(combined_template)
