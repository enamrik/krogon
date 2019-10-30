import krogon.either as E
import json
from krogon import krogon
from krogon import config
from krogon.steps.k8s import run_in_cluster, deployment, container
from krogon.yaml import load_all
from tests.helpers.mock_os_system import MockOsSystem
from base64 import b64encode
from tests.helpers.entry_mocks import mock_krogon_dsl


def test_can_generate_deployment_template():
    def _run_dsl(args):
        os: MockOsSystem = args["os_system"]
        project_id = "project1"
        app_name = 'test-service'
        cluster_name = 'prod-us-east1'
        kubectl_version = "v1.15.3"
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
                        deployment(app_name)
                            .with_empty_volume(name='test-volume')
                            .with_container(container('test', 'test:100'))
                            .with_container(container('test-2', 'test-2:100'))

                    ]
                )
            ],
            for_config=config(project_id, service_account_b64, output_template=True)
        )
        assert load_all(result[0][0])[0]['kind'] == 'Deployment'
        assert load_all(result[0][0])[0]['metadata']['name'] == app_name+'-dp'
        assert load_all(result[0][0])[0]['spec']['selector']['matchLabels']['app'] == app_name+'-app'
        assert load_all(result[0][0])[0]['spec']['template']['spec']['volumes'][0]['name'] == 'test-volume'
        container1 = load_all(result[0][0])[0]['spec']['template']['spec']['containers'][0]
        container2 = load_all(result[0][0])[0]['spec']['template']['spec']['containers'][1]
        assert container1['name'] == 'test-app'
        assert container1['image'] == 'test:100'
        assert container2['name'] == 'test-2-app'
        assert container2['image'] == 'test-2:100'

    mock_krogon_dsl(_run_dsl)
