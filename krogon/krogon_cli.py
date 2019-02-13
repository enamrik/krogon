import os
import krogon.config as c
import krogon.either as E
import krogon.file_system as fs
import krogon.scripts.scripter as scp
import krogon.os as krogon_os
import krogon.gcp.gcloud as gcp
import click
import krogon.ci.cloud_build.generate_cloudbuild_pipeline as cbp
from krogon.logger import Logger
from typing import Optional


@click.group()
def cli(): pass


@cli.command()
@click.option('--image-name', required=True, help='name of app image')
@click.option('--krogon-file', required=True, help='name of krogon file')
@click.option('--test-type', required=False, help='Optional: Test type: node, elixir, python')
@click.option('--test-cmd', required=False, help='Optional: Test command')
def generate_cloudbuild_pipeline(image_name: str,
                                 krogon_file: str,
                                 test_type: Optional[str],
                                 test_cmd: Optional[str]):
    """
    --image-name:   Name of the docker image to build. It's expected that a Dockerfile lives at the root of your repository.
    You can simply use your app name as the image name.

    --krogon-file:  The path to the krogon file. E.g. if the krogon file is in the root directory, the path would be ./release.krogon.py

    --test-type:    Optional. The test tooling platform. Supported: node, elixir, python

    --test-cmd:     Optional. The command to run your tests. E.g. npm test

    Notes:

        Steps to get your pipeline up and running in CloudBuild with Github.

        1. Go to https://github.com/marketplace/google-cloud-build and install the app on your github account.

        2. In the installation flow, pick the repository you want to build or let CloudBuild scan your account for all repositories with a cloudbuild.yaml file.

        3. In the installation flow, pick the Google project that's associated with the service Krogon uses. This
        will be the project where your jobs are run.

        4. Ensure your project's <id>@cloudbuild.gserviceaccount.com and the Krogon account has the following roles:

         * Cloud KMS Admin\n
         * Compute Admin\n
         * Storage Admin\n

        5. Now try running the generate_cloudbuild_pipeline command.
    """

    logger = Logger(name='krogon')
    config = _build_config()
    file_system = fs.file_system()
    gcloud = gcp.new_gcloud(config.service_account_info)

    cbp.generate_cloudbuild_pipeline(config, image_name, krogon_file,
                                     test_type, test_cmd, logger, file_system, gcloud) \
    | E.on | dict(success=lambda r: logger.info('DONE: {}'.format(r)),
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
