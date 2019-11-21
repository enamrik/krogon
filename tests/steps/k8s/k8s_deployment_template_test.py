import krogon.either as E
import json
from krogon import krogon
from krogon import config
from krogon.steps.k8s import run_in_cluster, deployment, container
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
        deployment_yaml = result[0][0].templates[0]
        assert deployment_yaml['kind'] == 'Deployment'
        assert deployment_yaml['metadata']['name'] == app_name+'-dp'
        assert deployment_yaml['spec']['selector']['matchLabels']['app'] == app_name+'-app'
        assert deployment_yaml['spec']['template']['spec']['volumes'][0]['name'] == 'test-volume'
        container1 = deployment_yaml['spec']['template']['spec']['containers'][0]
        container2 = deployment_yaml['spec']['template']['spec']['containers'][1]
        assert container1['name'] == 'test-app'
        assert container1['image'] == 'test:100'
        assert container2['name'] == 'test-2-app'
        assert container2['image'] == 'test-2:100'

    mock_krogon_dsl(_run_dsl)


def test_deployment_can_ensure_one_pod_at_a_time():
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
                            .with_ensure_only_one()
                            .with_empty_volume(name='test-volume')
                            .with_container(container('test', 'test:100'))
                            .with_container(container('test-2', 'test-2:100'))

                    ]
                )
            ],
            for_config=config(project_id, service_account_b64)
        )
        deployment_yaml = result[0][0].templates[0]
        assert deployment_yaml['spec']['replicas'] == 1
        assert deployment_yaml['spec']['strategy'] == {'type': 'Recreate'}

    mock_krogon_dsl(_run_dsl)


def test_deployment_can_set_rolling_update():
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
                            .with_rolling_update(max_surge='20%', max_unavailable='20%')
                            .with_empty_volume(name='test-volume')
                            .with_container(container('test', 'test:100'))
                            .with_container(container('test-2', 'test-2:100'))

                    ]
                )
            ],
            for_config=config(project_id, service_account_b64)
        )
        deployment_yaml = result[0][0].templates[0]
        assert deployment_yaml['spec']['strategy'] == {'rollingUpdate': {'maxSurge': '20%', 'maxUnavailable': '20%'},
                                                       'type': 'RollingUpdate'}

    mock_krogon_dsl(_run_dsl)
