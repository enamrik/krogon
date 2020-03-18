import click

from krogon.either_ext import chain
from krogon.config import config
from krogon.load_cli_modules import load_krogon_plugin_click_commands
import krogon.k8s.kubectl as k
import krogon.either as E


@click.group()
@click.pass_context
def cli(ctx):
    conf = config()
    cli_plugin_context = dict(
        conf=conf,
        kubectl=lambda cluster_name, command: k.discover_conn(cluster_name)(conf).cmd(command, cluster_name))
    ctx.obj = cli_plugin_context


load_krogon_plugin_click_commands(cli)


@cli.command()
def run_output():
    conf = config()
    cluster_names = conf.fs.directories_in(conf.output_dir)

    if len(cluster_names) == 0:
        print("No cluster directories in output folder")
        return

    def _run_in_cluster(cluster_name):
        template_files = conf.fs.files_in('{}/{}'.format(conf.output_dir, cluster_name))
        templates = [conf.fs.read(i) for i in template_files]
        k_ctl = k.discover_conn(cluster_name)(conf)
        return k_ctl.apply(templates, cluster_name)

    chain(cluster_names, lambda cluster_name: _run_in_cluster(cluster_name)) \
    | E.on | dict(success=lambda c: conf.log.info('DONE:'),
                  failure=lambda e: conf.log.error('FAILED: {}'.format(e)))


def main():
    cli()


if __name__ == "__main__":
    cli()
