import click
from krogon.exec_context import ExecContext
from krogon.config import config, Config
from krogon.load_cli_modules import load_krogon_plugin_click_commands
import krogon.gcp.gcloud as g
import krogon.k8s.kubectl as k
import python_either.either as E
from pprint import pprint


@click.group()
@click.pass_context
def cli(ctx):
    context = ExecContext(config())
    cli_plugin_context = dict(
        project_id=context.config.project_id,
        service_account_b64=context.config.service_account_b64,
        krogon_install_url=context.config.krogon_install_url,
        kubectl=lambda cluster_name, command: k.kubectl(context.kubectl, cluster_name, command))
    ctx.obj = cli_plugin_context


load_krogon_plugin_click_commands(cli)


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
