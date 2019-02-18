import krogon.either as E
import krogon.k8s.kubectl as k
import krogon.ci.cloud_build.cloudbuild_cli as cloudbuild_cli
import krogon.ci.gocd.gocd_cli as gocd_cli
import click
import krogon.gcp.gcloud as gcp
from krogon.os import new_os
from krogon.file_system import FileSystem
from krogon.logger import Logger
from krogon.cli.builders import build_config


@click.group()
def cli(): pass


cli.add_command(cloudbuild_cli.cloudbuild)
cli.add_command(gocd_cli.gocd)


@cli.command()
@click.option('--cluster-name', required=True, help='name of cluster')
@click.option('--port', required=True, help='port to forward')
def proxy(cluster_name: str, port: str):
    logger = Logger(name='krogon')
    config = build_config()
    os = new_os()
    file = FileSystem()
    gcloud = gcp.new_gcloud(config, file, os, logger)
    k_ctl = k.KubeCtl(config, os, logger, gcloud, file)

    k.proxy(k_ctl, cluster_name, port) \
        | E.on | dict(success=lambda _: logger.info('DONE'),
                      failure=lambda e: logger.error('FAILED: {}'.format(e)))


@cli.command()
@click.option('--cluster-name', required=True, help='name of cluster')
def get_access_token(cluster_name: str):
    logger = Logger(name='krogon')
    config = build_config()
    os = new_os()
    file = FileSystem()
    gcloud = gcp.new_gcloud(config, file, os, logger)

    gcp.get_access_token(gcloud, cluster_name) \
        | E.on | dict(success=lambda _: logger.info('DONE'),
                      failure=lambda e: logger.error('FAILED: {}'.format(e)))


@cli.command()
@click.option('--cluster-name', required=True, help='name of cluster')
@click.option('--command', required=True, help='name of cluster')
def kubectl(cluster_name: str, command: str):
    logger = Logger(name='krogon')
    config = build_config()
    os = new_os()
    file = FileSystem()
    gcloud = gcp.new_gcloud(config, file, os, logger)
    k_ctl = k.KubeCtl(config, os, logger, gcloud, file)

    k.kubectl(k_ctl, cluster_name, command) \
        | E.on | dict(success=lambda _: logger.info('DONE'),
                      failure=lambda e: logger.error('FAILED: {}'.format(e)))


def main():
    cli()


if __name__ == "__main__":
    cli()
