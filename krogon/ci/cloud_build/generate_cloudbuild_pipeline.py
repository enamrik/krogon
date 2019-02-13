import krogon.file_system as fs
import krogon.gcp.cloud_build.cloud_build as cb
import krogon.gcp.gcloud as gc
import krogon.either as E
import krogon.maybe as M
import krogon.yaml as yaml
import krogon.gcp.kms.cloud_kms as kms
from krogon.config import Config
from krogon.logger import Logger
from krogon.nullable import nlist
from typing import Optional


def generate_cloudbuild_pipeline(config: Config,
                                 image_name: str,
                                 krogon_file_path: str,
                                 test_agent_type: Optional[str],
                                 test_agent_cmd: Optional[str],
                                 logger: Logger, file: fs.FileSystem, gcloud: gc.GCloud):

    krogon_image_name = _krogon_image(config.project_id, config.krogon_version)
    key_region = 'us-east1'
    maybe_test_step = _build_test_agent_step(test_agent_type, test_agent_cmd)

    return cb.new_cloud_build(gcloud, logger) \
           | E.then | (lambda c_build:
                       _create_krogon_agent(config.project_id, config.krogon_version, krogon_image_name, c_build)) \
           | E.then | (lambda _:
                       _store_key(config.service_account_b64, config.project_id, key_region, gcloud, logger)) \
           | E.then | (lambda secret_entry:
                       _build_pipeline_template(config.project_id, image_name, krogon_file_path,
                                                krogon_image_name, maybe_test_step, secret_entry)) \
           | E.then | (lambda template:
                       _write_pipeline(template, file))


def _write_pipeline(template: dict, file: fs.FileSystem):
    return file.write(file.cwd() + '/cloudbuild.yaml', yaml.dump(template))


def _build_pipeline_template(project_id: str, image_name: str,
                             krogon_file_path:str,
                             krogon_image_name: str,
                             test_step: M.Maybe[dict],
                             secret_entry: dict):

    image = 'gcr.io/{}/{}:$COMMIT_SHA'.format(project_id, image_name)

    return {
        'steps': nlist()
            .append_if_value(test_step)
            .append({
                'name': 'gcr.io/cloud-builders/docker',
                'id': 'Build Image',
                'args': ['build', '-t', image, '.']
            })
            .append({
                'name': 'gcr.io/cloud-builders/docker',
                'id': 'Push Image',
                'args': ['push', image]
            })
            .append({
                'name': krogon_image_name,
                'id': 'Deploy App: {}'.format(image_name),
                'args': ['python', krogon_file_path],
                'env': ['GCP_PROJECT={}'.format(project_id),
                        'VERSION=$COMMIT_SHA'],
                'secretEnv': ['GCP_SERVICE_ACCOUNT_B64']
            })
            .to_list(),
        'secrets': [secret_entry]
    }


def _store_key(service_account_b64, project_id: str, region: str, gcloud: gc.GCloud, logger: Logger):

    def _cloud_build_secret(resp):
        return {
            'kmsKeyName': resp['key_full_name'],
            'secretEnv': {'GCP_SERVICE_ACCOUNT_B64': resp['ciphertext']}
        }

    return kms.new_cloud_kms(gcloud, logger) \
           | E.then | (lambda c_kms: kms.encrypt(c_kms,
                                                 key='krogon-user',
                                                 value=service_account_b64,
                                                 project_id=project_id,
                                                 region=region)) \
           | E.then | (lambda r: _cloud_build_secret(r))


def _build_test_agent_step(test_agent_type: Optional[str],
                           test_agent_cmd: Optional[str]):

    if test_agent_type is None:
        return M.Nothing()

    test_steps = {
        'node': {
            'name': 'gcr.io/cloud-builders/npm',
            'args': ['test']
        },
        'elixir': {
            'name': 'elixir:1.8.0',
            'args': ['mix', 'test']
        },
        'python': {
            'name': 'python',
            'args': ['pytest']
        }
    }
    step = test_steps[test_agent_type]
    step['id'] = 'Run Tests'

    if test_agent_cmd is not None:
        step['args'] = test_agent_cmd.split(' ')

    return M.Just(step)


def _create_krogon_agent(project_id:str, krogon_version: str, krogon_image_name: str, c_build: cb.CloudBuild):

    template = _build_krogon_agent_template(krogon_version, krogon_image_name)
    return cb.create(c_build, project_id, template)


def _build_krogon_agent_template(krogon_version: str, krogon_image_name: str):
    return {
        'steps': [
            {
                'name': 'gcr.io/cloud-builders/git',
                'args': ['clone', '--branch', krogon_version, 'https://github.com/enamrik/krogon']
            },
            {
                'name': 'python',
                'args': ['cp', './krogon/krogon/ci/cloud_build/Dockerfile', './krogon']
            },
            {
                'name': 'gcr.io/cloud-builders/docker',
                'args': ['build', '-t', krogon_image_name, './krogon']
            }
        ],
        'images': [krogon_image_name]
    }


def _krogon_image(project_id: str, version: str):
    return 'gcr.io/{project_id}/krogon:{version}'.format(project_id=project_id, version=version)