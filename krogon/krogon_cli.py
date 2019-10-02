import click

from krogon.either_ext import chain
from krogon.exec_context import ExecContext
from krogon.config import config, Config
from krogon.file_system import FileSystem
from krogon.load_cli_modules import load_krogon_plugin_click_commands
import krogon.gcp.gcloud as g
import krogon.k8s.kubectl as k
import krogon.either as E


@click.group()
@click.pass_context
def cli(ctx):
    context = ExecContext(config())
    cli_plugin_context = dict(
        project_id=context.config.get_project_id(),
        service_account_b64=context.config.get_service_account_b64(),
        krogon_install_url=context.config.krogon_install_url,
        kubectl=lambda cluster_name, command: k.kubectl(context.kubectl, cluster_name, command))
    ctx.obj = cli_plugin_context


load_krogon_plugin_click_commands(cli)


@cli.command()
def run_output():
    context = ExecContext(config())
    fs: FileSystem = context.fs
    cluster_names = fs.directories_in(context.config.output_dir)

    if len(cluster_names) == 0:
        print("No cluster directories in output folder")
        return

    def _run_in_cluster(cluster_name):
        template_files = fs.files_in('{}/{}'.format(context.config.output_dir, cluster_name))
        templates = [fs.read(i) for i in template_files]
        return k.apply(context.kubectl, templates, cluster_name)

    chain(cluster_names, lambda cluster_name: _run_in_cluster(cluster_name)) \
    | E.on | dict(success=lambda c: context.logger.info('DONE:'),
                  failure=lambda e: context.logger.error('FAILED: {}'.format(e)))


@cli.command()
def clusters():
    context = ExecContext(config())

    g.get_all_clusters(context.gcloud) \
    | E.on | dict(success=lambda c: context.logger.info('DONE: \n\n{}'.format(c)),
                  failure=lambda e: context.logger.error('FAILED: {}'.format(e)))


@cli.command()
@click.option('--cluster-name', required=True, help='name of cluster')
def kubeconfig(cluster_name: str):
    context = ExecContext(config())

    g.configure_kubeconfig_path(context.gcloud, cluster_name) \
    | E.on | dict(success=lambda path: context.logger.info('DONE: \n\nRun the following command:\n\nexport '
                                                           'KUBECONFIG={}  \n'.format(path)),
                  failure=lambda e: context.logger.error('FAILED: {}'.format(e)))


@cli.command()
@click.option('--cluster-name', required=True, help='name of cluster')
def access_token(cluster_name: str):
    context = ExecContext(config())

    g.get_access_token(context.gcloud, cluster_name) \
    | E.on | dict(success=lambda _: context.logger.info('DONE'),
                  failure=lambda e: context.logger.error('FAILED: {}'.format(e)))


def main():
    cli()


if __name__ == "__main__":
    cli()
