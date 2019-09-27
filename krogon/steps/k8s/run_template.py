from krogon.exec_context import ExecContext


def run_template(template, context: ExecContext):
    if hasattr(template, 'run'):
        template_dicts = template.run()
        context.append_templates(template_dicts)
        return context

    if hasattr(template, 'map_context'):
        return template.map_context(context)

    return "failure", "Unsupported template type: {}".format(type(template))
