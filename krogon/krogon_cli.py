import click
import os
import krogon.gcp.deployment_manager.deployment_manager as dm
import krogon.config as c
import krogon.either as E
import krogon.file_system as fs
import krogon.scripts.scripter as scp
import krogon.os as krogon_os
import krogon.gcp.gcloud as gcp
from krogon.logger import Logger


@click.group()
def cli(): pass


@cli.command()
@click.option('--name', required=True, help='name of deployment')
def delete_deployment(name: str):
    logger = Logger(name='krogon')
    config = _build_config()
    gcloud = gcp.new_gcloud(config.service_account_info)

    gcloud.deployment_manager(logger) \
        | E.then | (lambda d_manager: dm.delete(d_manager, config.project_id, name)) \
        | E.on | dict(success=lambda _: logger.info('DONE'),
                      failure=lambda e: logger.error('FAILED: {}'.format(e)))


@cli.command()
@click.option('--cluster-name', required=True, help='name of cluster')
@click.option('--port', required=True, help='port to forward')
def proxy(cluster_name: str, port: str):
    logger = Logger(name='krogon')
    config = _build_config()
    scripter = _build_scripter(config, logger)

    scp.proxy(scripter, cluster_name, port) \
        | E.on | dict(success=lambda _: logger.info('DONE'),
                      failure=lambda e: logger.error('FAILED: {}'.format(e)))


@cli.command()
@click.option('--cluster-name', required=True, help='name of cluster')
def get_access_token(cluster_name: str):
    logger = Logger(name='krogon')
    config = _build_config()
    scripter = _build_scripter(config, logger)

    scp.get_access_token(scripter, cluster_name) \
        | E.on | dict(success=lambda _: logger.info('DONE'),
                      failure=lambda e: logger.error('FAILED: {}'.format(e)))


@cli.command()
@click.option('--cluster-name', required=True, help='name of cluster')
@click.option('--gclb-name', required=True, help='name of Global Load Balancer')
def remove_cluster_from_gclb(cluster_name: str, gclb_name: str):
    logger = Logger(name='krogon')
    config = _build_config()
    scripter = _build_scripter(config, logger)

    scp.remove_gclb_cluster(scripter, cluster_name, gclb_name) \
    | E.on | dict(success=lambda _: logger.info('DONE'),
                  failure=lambda e: logger.error('FAILED: {}'.format(e)))


@cli.command()
@click.option('--cluster-name', required=True, help='name of cluster')
@click.option('--command', required=True, help='name of cluster')
def kubectl(cluster_name: str, command: str):
    logger = Logger(name='krogon')
    config = _build_config()
    scripter = _build_scripter(config, logger)

    scp.kubectl(scripter, cluster_name, command) \
    | E.on | dict(success=lambda _: logger.info('DONE'),
                  failure=lambda e: logger.error('FAILED: {}'.format(e)))


def _build_scripter(config: c.Config, logger: Logger):
    file_system = fs.file_system()
    os_system = krogon_os.new_os()
    return scp.Scripter(config.project_id, config.service_account_info, os_system, file_system, logger)


def _build_config():
    return c.config(project_id=os.environ['GCP_PROJECT'],
                    service_account_b64=os.environ['GCP_SERVICE_ACCOUNT_B64'])


def main():
    cli()


if __name__ == "__main__":
    cli()
