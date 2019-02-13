from krogon.krogon_cli import generate_cloudbuild_pipeline
from base64 import b64encode
from tests.helpers import MockLogger, MockGCloud, MockFileSystem, MockOsSystem
from krogon.config import Config
from unittest.mock import Mock
from tests.helpers.mocks import MockSetup, Setup
from tests.helpers import mock_krogon_cli
from click.testing import CliRunner
import click
import krogon.either as E
import krogon.yaml as yaml
import json


def test_generate_pipeline():
    project_id = "project1"
    service_account_b64 = b64encode(json.dumps({'key': 'someKey'}).encode('utf-8')).decode('utf-8')

    def _run_cli(args):
        gcloud: MockGCloud = args['gcloud']
        file_system: MockFileSystem = args['file_system']
        image_name = 'test-app'
        krogon_file_path = './release.krogon.py'
        runner = args['cli_runner']
        cli_assert = args['cli_assert']
        krogon_version = '0.0.2'
        plain_text = b64encode(service_account_b64.encode('utf-8')).decode('utf-8')
        encrypted_text = 'someEncryptedText'
        build_id = 'someBuildId'
        build_body = {'steps': [
            {'name': 'gcr.io/cloud-builders/git',
             'args': ['clone', '--branch', krogon_version, 'https://github.com/enamrik/krogon']},
            {'name': 'python',
             'args': ['cp', './krogon/krogon/ci/cloud_build/Dockerfile', './krogon']},
            {'name': 'gcr.io/cloud-builders/docker',
             'args': ['build', '-t', 'gcr.io/'+project_id+'/krogon:'+krogon_version, './krogon']}],
            'images': ['gcr.io/'+project_id+'/krogon:'+krogon_version]}

        MockSetup.mock_one(file_system.get_mock().read,
                           args=['{}/./VERSION'.format(MockFileSystem.krogon_dir())],
                           return_values=['0.0.2'])

        gcloud.mock_path('projects().locations().keyRings().cryptoKeys().encrypt()',
                         kwargs={
                             'name': 'projects/{}/locations/us-east1/keyRings/'
                                     'krogon-user-keyring/cryptoKeys/krogon-user'.format(project_id),
                             'body': {'plaintext': plain_text}},
                         exec_returns=[{'ciphertext': encrypted_text}])

        gcloud.mock_path('projects().builds().get()',
                         kwargs={ 'projectId': project_id, 'id': build_id},
                         exec_returns=[{'status': 'WORKING'}, {'status': 'SUCCESS'}])

        gcloud.mock_path('projects().builds().create()',
                         kwargs={
                             'projectId': project_id,
                             'body': build_body},
                         exec_returns=[{'metadata': {'build': {'id': build_id}}}])

        result = runner.invoke(generate_cloudbuild_pipeline, [
            '--image-name', image_name,
            '--krogon-file', krogon_file_path])
        cli_assert(result)

        expected_pipeline = {
            'steps': [
                {'name': 'gcr.io/cloud-builders/docker',
                 'id': 'Build Image',
                 'args': ['build', '-t', 'gcr.io/{}/test-app:$COMMIT_SHA'.format(project_id), '.']},
                {'name': 'gcr.io/cloud-builders/docker',
                 'id': 'Push Image',
                 'args': ['push', 'gcr.io/{}/{}:$COMMIT_SHA'.format(project_id, image_name)]},
                {'name': 'gcr.io/{}/krogon:{}'.format(project_id, krogon_version),
                 'id': 'Deploy App: '+image_name,
                 'args': ['python', './release.krogon.py'],
                 'env': [
                     'GCP_PROJECT={}'.format(project_id),
                     'VERSION=$COMMIT_SHA'
                 ],
                 'secretEnv': ['GCP_SERVICE_ACCOUNT_B64']}],
            'secrets': [
                {'kmsKeyName': 'projects/{}/locations/us-east1/keyRings/krogon-user-keyring/cryptoKeys/krogon-user'
                    .format(project_id),
                 'secretEnv': {'GCP_SERVICE_ACCOUNT_B64': encrypted_text}} ]
        }
        MockSetup.setup(file_system.get_mock().write, index=0).expected_to_have_been_called(
            with_args=['{}/cloudbuild.yaml'.format(MockFileSystem.cwd()), yaml.dump(expected_pipeline)])

    mock_krogon_cli(_run_cli,env={'GCP_PROJECT': project_id,
                                  'GCP_SERVICE_ACCOUNT_B64': service_account_b64})


def test_generate_pipeline_with_test_step():
    project_id = "project1"
    service_account_b64 = b64encode(json.dumps({'key': 'someKey'}).encode('utf-8')).decode('utf-8')

    def _run_cli(args):
        gcloud: MockGCloud = args['gcloud']
        file_system: MockFileSystem = args['file_system']
        image_name = 'test-app'
        krogon_file_path = './release.krogon.py'
        runner = args['cli_runner']
        cli_assert = args['cli_assert']
        test_agent_type = 'node'
        test_agent_command = 'npm run unit-test'
        krogon_version = '0.0.2'
        plain_text = b64encode(service_account_b64.encode('utf-8')).decode('utf-8')
        encrypted_text = 'someEncryptedText'
        build_id = 'someBuildId'
        build_body = {'steps': [
            {'name': 'gcr.io/cloud-builders/git',
             'args': ['clone', '--branch', krogon_version, 'https://github.com/enamrik/krogon']},
            {'name': 'python',
             'args': ['cp', './krogon/krogon/ci/cloud_build/Dockerfile', './krogon']},
            {'name': 'gcr.io/cloud-builders/docker',
             'args': ['build', '-t', 'gcr.io/'+project_id+'/krogon:'+krogon_version, './krogon']}],
            'images': ['gcr.io/'+project_id+'/krogon:'+krogon_version]}

        MockSetup.mock_one(file_system.get_mock().read,
                           args=['{}/./VERSION'.format(MockFileSystem.krogon_dir())],
                           return_values=['0.0.2'])

        gcloud.mock_path('projects().locations().keyRings().cryptoKeys().encrypt()',
                         kwargs={
                             'name': 'projects/{}/locations/us-east1/keyRings/'
                                     'krogon-user-keyring/cryptoKeys/krogon-user'.format(project_id),
                             'body': {'plaintext': plain_text}},
                         exec_returns=[{'ciphertext': encrypted_text}])

        gcloud.mock_path('projects().builds().get()',
                         kwargs={ 'projectId': project_id, 'id': build_id},
                         exec_returns=[{'status': 'WORKING'}, {'status': 'SUCCESS'}])

        gcloud.mock_path('projects().builds().create()',
                         kwargs={
                             'projectId': project_id,
                             'body': build_body},
                         exec_returns=[{'metadata': {'build': {'id': build_id}}}])

        result = runner.invoke(generate_cloudbuild_pipeline, [
            '--image-name', image_name,
            '--krogon-file', krogon_file_path,
            '--test-type', test_agent_type,
            '--test-cmd', test_agent_command])
        cli_assert(result)

        expected_pipeline = {
            'steps': [
                {'name': 'gcr.io/cloud-builders/npm',
                 'args': ['npm', 'run', 'unit-test'],
                 'id': 'Run Tests'},
                {'name': 'gcr.io/cloud-builders/docker',
                 'id': 'Build Image',
                 'args': ['build', '-t', 'gcr.io/{}/test-app:$COMMIT_SHA'.format(project_id), '.']},
                {'name': 'gcr.io/cloud-builders/docker',
                 'id': 'Push Image',
                 'args': ['push', 'gcr.io/{}/{}:$COMMIT_SHA'.format(project_id, image_name)]},
                {'name': 'gcr.io/{}/krogon:{}'.format(project_id, krogon_version),
                 'id': 'Deploy App: '+image_name,
                 'args': ['python', './release.krogon.py'],
                 'env': [
                     'GCP_PROJECT={}'.format(project_id),
                     'VERSION=$COMMIT_SHA'
                 ],
                 'secretEnv': ['GCP_SERVICE_ACCOUNT_B64']}],
            'secrets': [
                {'kmsKeyName': 'projects/{}/locations/us-east1/keyRings/krogon-user-keyring/cryptoKeys/krogon-user'
                    .format(project_id),
                 'secretEnv': {'GCP_SERVICE_ACCOUNT_B64': encrypted_text}} ]
        }
        MockSetup.setup(file_system.get_mock().write, index=0).expected_to_have_been_called(
            with_args=['{}/cloudbuild.yaml'.format(MockFileSystem.cwd()), yaml.dump(expected_pipeline)])

    mock_krogon_cli(_run_cli,env={'GCP_PROJECT': project_id,
                                  'GCP_SERVICE_ACCOUNT_B64': service_account_b64})
