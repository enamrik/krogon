import krogon.either as E
import json
from krogon import krogon
from krogon import config
from krogon.steps.k8s import run_in_cluster, micro_service
from krogon.yaml import load_all
from tests.helpers.mock_os_system import MockOsSystem
from base64 import b64encode
from tests.helpers.entry_mocks import mock_krogon_dsl


def test_can_generate_micro_service_template():
    def _run_dsl(args):
        os: MockOsSystem = args["os_system"]
        project_id = "project1"
        service_name = 'test-service'
        cluster_name = 'prod-us-east1'
        kubectl_version = "v1.15.3"
        image_url = "test-service:1.0.0"
        app_port = 3000
        service_port = 80
        service_account_b64 = b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))

        os.mock_clusters_list([cluster_name])
        os.mock_kubernetes_release(E.success(kubectl_version))
        os.mock_download_install_kubectl(kubectl_version, E.success())
        os.mock_create_kube_config(cluster_name, E.success())
        os.mock_kubectl_apply_temp_file(cluster_name, E.success())

        _, result = krogon(
            run_steps=[
                run_in_cluster(
                    named=cluster_name,
                    templates=[
                        micro_service(service_name, image_url, app_port)
                    ]
                )
            ],
            for_config=config(project_id, service_account_b64, output_template=True)
        )
        assert load_all(result[0])[0]['kind'] == 'Service'
        assert load_all(result[0])[0]['metadata']['name'] == service_name
        assert load_all(result[0])[0]['spec']['selector']['app'] == service_name+'-app'
        assert load_all(result[0])[0]['spec']['ports'][0]['targetPort'] == app_port
        assert load_all(result[0])[0]['spec']['ports'][0]['port'] == service_port

        assert load_all(result[0])[1]['kind'] == 'Deployment'

    mock_krogon_dsl(_run_dsl)


def test_can_set_secret():
    def _run_dsl(args):
        os: MockOsSystem = args["os_system"]
        project_id = "project1"
        service_name = 'test-service'
        cluster_name = 'prod-us-east1'
        kubectl_version = "v1.15.3"
        image_url = "test-service:1.0.0"
        app_port = 3000
        service_account_b64 = b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))

        os.mock_clusters_list([cluster_name])
        os.mock_kubernetes_release(E.success(kubectl_version))
        os.mock_download_install_kubectl(kubectl_version, E.success())
        os.mock_create_kube_config(cluster_name, E.success())
        os.mock_kubectl_apply_temp_file(cluster_name, E.success())

        _, result = krogon(
            run_steps=[
                run_in_cluster(
                    named=cluster_name,
                    templates=[
                        micro_service(service_name, image_url, app_port)
                            .with_environment_secret('coolSecret', {'ENV_NAME': 'secretkey'})
                    ]
                )
            ],
            for_config=config(project_id, service_account_b64, output_template=True)
        )
        assert load_all(result[0])[1]['kind'] == 'Deployment'
        container = load_all(result[0])[1]['spec']['template']['spec']['containers'][0]
        assert container['env'][0]['name'] == 'ENV_NAME'
        assert container['env'][0]['valueFrom']['secretKeyRef']['name'] == 'coolSecret'
        assert container['env'][0]['valueFrom']['secretKeyRef']['key'] == 'secretkey'

    mock_krogon_dsl(_run_dsl)
