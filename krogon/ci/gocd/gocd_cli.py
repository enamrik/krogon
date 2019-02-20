import krogon.either as E
import krogon.file_system as fs
import krogon.k8s.kubectl as k
import click
import krogon.ci.gocd.agent_image as agent_image
import krogon.ci.gocd.generate_pipeline as gp
import krogon.ci.gocd.encrypt_secret as es
import krogon.gcp.gcloud as gcp
from krogon.os import new_os
from krogon.logger import Logger
from krogon.cli.builders import build_config


@click.group()
def gocd(): pass


@gocd.command()
@click.option('--app-name', required=True, help='Name of app. Can also be the name of the git repo')
@click.option('--git-url', required=True, help='Git url of repository')
@click.option('--username', required=True, help='GoCD username')
@click.option('--password', required=True, help='GoCD password')
@click.option('--cluster-name', required=True, help='Cluster where GoCD is hosted')
def register_pipeline(app_name: str,
                      git_url: str,
                      username: str,
                      password: str,
                      cluster_name: str):

    logger = Logger(name='krogon')
    config = build_config()
    file = fs.file_system()
    os = new_os()
    gcloud = gcp.new_gcloud(config, file, os, logger)
    k_ctl = k.KubeCtl(config, os, logger, gcloud, file)

    gp.register_pipeline(k_ctl, app_name, git_url, username, password, cluster_name) \
    | E.on | dict(success=lambda r: logger.info('DONE: {}'.format(r)),
                  failure=lambda e: logger.error('FAILED: {}'.format(e)))


@gocd.command()
@click.option('--app-name', required=True, help='Name of app. Can also be the name of the git repo')
@click.option('--git-url', required=True, help='Git url of repository')
@click.option('--krogon-agent-name', required=True, help='GoCD krogon agent\'s elastic profile id')
@click.option('--krogon-file', required=True, help='Krogon file for deployment stage')
@click.option('--username', required=True, help='GoCD username')
@click.option('--password', required=True, help='GoCD password')
@click.option('--cluster-name', required=True, help='Cluster where GoCD is hosted')
def generate_pipeline(app_name: str,
                      git_url: str,
                      krogon_agent_name: str,
                      krogon_file: str,
                      username: str,
                      password: str,
                      cluster_name: str):

    logger = Logger(name='krogon')
    config = build_config()
    file = fs.file_system()
    os = new_os()
    gcloud = gcp.new_gcloud(config, file, os, logger)
    k_ctl = k.KubeCtl(config, os, logger, gcloud, file)

    gp.generate_pipeline(k_ctl, file, config.project_id, config.service_account_b64, app_name, git_url,
                         krogon_agent_name, krogon_file, username, password, cluster_name) \
    | E.on | dict(success=lambda r: logger.info('DONE: {}'.format(r)),
                  failure=lambda e: logger.error('FAILED: {}'.format(e)))


@gocd.command()
@click.option('--plain-text', required=True, help='Plain text to encrypt')
@click.option('--username', required=True, help='GoCD username')
@click.option('--password', required=True, help='GoCD password')
@click.option('--cluster-name', required=True, help='Cluster where GoCD is hosted')
def encrypt_secret(plain_text: str, username: str, password: str, cluster_name: str):
    logger = Logger(name='krogon')
    config = build_config()
    file = fs.file_system()
    os = new_os()
    gcloud = gcp.new_gcloud(config, file, os, logger)
    k_ctl = k.KubeCtl(config, os, logger, gcloud, file)

    es.encrypt_secret(k_ctl, plain_text, username, password, cluster_name) \
    | E.on | dict(success=lambda r: logger.info('DONE: \n\nENCRYPTED TEXT: {}'.format(r)),
                  failure=lambda e: logger.error('FAILED: {}'.format(e)))


@gocd.command()
@click.option('--agent-name', required=True, help='GoCD agent\'s elastic profile id')
@click.option('--image-url', required=True, help='Docker fully qualified image name on which agent is based')
@click.option('--out-dir', required=True, help='Directory where Dockerfile should be stored')
def generate_agent_template(agent_name: str, out_dir: str, image_url: str):
    logger = Logger(name='krogon')
    file_system = fs.file_system()

    agent_image.generate_agent_template(file_system, agent_name,  out_dir, image_url) \
    | E.on | dict(success=lambda r: logger.info('DONE: {}'.format(r)),
                  failure=lambda e: logger.error('FAILED: {}'.format(e)))


@gocd.command()
@click.option('--agent-name', required=True, help='GoCD agent\'s elastic profile id')
@click.option('--agent-template-path', required=True, help='file path and name where template was stored')
@click.option('--image-url', required=True, help='Docker fully qualified image name on which agent is based')
@click.option('--cluster-name', required=True, help='Name of cluster where GoCD is hosted')
@click.option('--username', required=True, help='GoCD username')
@click.option('--password', required=True, help='GoCD password')
def register_agent_template(agent_name: str, agent_template_path: str, image_url,
                            username: str, password: str, cluster_name: str):
    file_system = fs.file_system()
    logger = Logger(name='krogon')
    config = build_config()
    file = fs.file_system()
    os = new_os()
    gcloud = gcp.new_gcloud(config, file, os, logger)
    k_ctl = k.KubeCtl(config, os, logger, gcloud, file)

    agent_image.register_agent_template(k_ctl, file_system, agent_name, agent_template_path,
                                        image_url, username, password, cluster_name) \
    | E.on | dict(success=lambda r: logger.info('DONE: {}'.format(r)),
                  failure=lambda e: logger.error('FAILED: {}'.format(e)))


