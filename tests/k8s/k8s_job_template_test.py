import krogon.either as E
import json
from krogon import run_in_cluster,  gke_conn
from krogon.k8s import cron_job
from tests.helpers.mock_file_system import find_write_template_calls, MockFileSystem
from tests.helpers.mock_os_system import MockOsSystem
from base64 import b64encode
from tests.helpers.entry_mocks import mock_krogon_dsl


def test_can_generate_cron_job_template():
    def _run_dsl(args):
        os: MockOsSystem = args["os_system"]
        fs: MockFileSystem = args['file_system']
        project_id = "project1"
        job_name = 'test-service'
        cluster_name = 'prod-us-east1'
        kubectl_version = "v1.15.3"
        image_url = "test-service:1.0.0"
        service_account_b64 = b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))

        os.mock_clusters_list([cluster_name])
        os.mock_kubernetes_release(E.success(kubectl_version))
        os.mock_download_install_kubectl(kubectl_version, E.success())
        os.mock_create_kube_config(cluster_name, E.success())
        os.mock_kubectl_apply_temp_file(cluster_name, E.success())

        _, result = run_in_cluster(
            conn=gke_conn(cluster_name, project_id, service_account_b64),
            templates=[
                cron_job(job_name, image_url)
            ]
        )

        yamls = find_write_template_calls(fs)
        assert yamls[0]['kind'] == 'CronJob'
        assert yamls[0]['metadata']['name'] == job_name
        container = yamls[0]['spec']['jobTemplate']['spec']['template']['spec']['containers'][0]
        assert container['name'] == job_name
        assert container['image'] == image_url

    mock_krogon_dsl(_run_dsl)


def test_can_set_secret_for_job():
    def _run_dsl(args):
        fs: MockFileSystem = args['file_system']
        os: MockOsSystem = args["os_system"]
        project_id = "project1"
        job_name = 'test-service'
        cluster_name = 'prod-us-east1'
        kubectl_version = "v1.15.3"
        image_url = "test-service:1.0.0"
        service_account_b64 = b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))

        os.mock_clusters_list([cluster_name])
        os.mock_kubernetes_release(E.success(kubectl_version))
        os.mock_download_install_kubectl(kubectl_version, E.success())
        os.mock_create_kube_config(cluster_name, E.success())
        os.mock_kubectl_apply_temp_file(cluster_name, E.success())

        _, result = run_in_cluster(
            conn=gke_conn(cluster_name, project_id, service_account_b64),
            templates=[
                cron_job(job_name, image_url)
                    .with_environment_secret('coolSecret', {'ENV_NAME': 'secretkey'})
            ]
        )

        yamls = find_write_template_calls(fs)
        container = yamls[0]['spec']['jobTemplate']['spec']['template']['spec']['containers'][0]
        assert container['env'][0]['name'] == 'ENV_NAME'
        assert container['env'][0]['valueFrom']['secretKeyRef']['name'] == 'coolSecret'
        assert container['env'][0]['valueFrom']['secretKeyRef']['key'] == 'secretkey'

    mock_krogon_dsl(_run_dsl)
