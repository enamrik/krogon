import krogon.either as E
import json
from krogon import run_in_cluster, gen_template, gke_conn
from krogon.k8s import deployment, container
from tests.helpers.mock_file_system import MockFileSystem, find_write_template_calls
from tests.helpers.mock_os_system import MockOsSystem
from base64 import b64encode
from tests.helpers.entry_mocks import mock_krogon_dsl


def test_deployment_can_generate_deployment_template():
    def _run_dsl(args):
        os: MockOsSystem = args["os_system"]
        fs: MockFileSystem = args["file_system"]
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

        _, result = run_in_cluster(
            conn=gke_conn(cluster_name, project_id, service_account_b64),
            templates=[
                deployment(app_name)
                    .with_empty_volume(name='test-volume')
                    .with_container(container('test', 'test:100'))
                    .with_container(container('test-2', 'test-2:100'))

            ]
        )
        deployment_yaml = find_write_template_calls(fs)[0]
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
        fs: MockFileSystem = args["file_system"]
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

        _, result = run_in_cluster(
            conn=gke_conn(cluster_name, project_id, service_account_b64),
            templates=[
                deployment(app_name)
                    .with_ensure_only_one()
                    .with_empty_volume(name='test-volume')
                    .with_container(container('test', 'test:100'))
                    .with_container(container('test-2', 'test-2:100'))

            ]
        )
        deployment_yaml = find_write_template_calls(fs)[0]
        assert deployment_yaml['spec']['replicas'] == 1
        assert deployment_yaml['spec']['strategy'] == {'type': 'Recreate'}

    mock_krogon_dsl(_run_dsl)


def test_deployment_can_set_rolling_update():
    def _run_dsl(args):
        os: MockOsSystem = args["os_system"]
        fs: MockFileSystem = args["file_system"]
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

        _, result = run_in_cluster(
            conn=gke_conn(cluster_name, project_id, service_account_b64),
            templates=[
                deployment(app_name)
                    .with_rolling_update(max_surge='20%', max_unavailable='20%')
                    .with_empty_volume(name='test-volume')
                    .with_container(container('test', 'test:100'))
                    .with_container(container('test-2', 'test-2:100'))

            ]
        )
        deployment_yaml = find_write_template_calls(fs)[0]
        assert deployment_yaml['spec']['strategy'] == {'rollingUpdate': {'maxSurge': '20%', 'maxUnavailable': '20%'},
                                                       'type': 'RollingUpdate'}

    mock_krogon_dsl(_run_dsl)


def test_deployment_can_set_deployment_empty_volume():
    def _run_dsl(args):
        os: MockOsSystem = args["os_system"]
        fs: MockFileSystem = args["file_system"]
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

        _, result = run_in_cluster(
            conn=gke_conn(cluster_name, project_id, service_account_b64),
            templates=[
                deployment(app_name)
                    .with_rolling_update(max_surge='20%', max_unavailable='20%')
                    .with_empty_volume(name='test-volume')
                    .with_container(container('test', 'test:100')
                                    .with_volume_mount('test-volume', '/var/data/my-data'))

            ]
        )
        deployment_yaml = find_write_template_calls(fs)[0]
        assert deployment_yaml['spec']['template']['spec']['volumes'] == [{'emptyDir': {}, 'name': 'test-volume'}]
        assert deployment_yaml['spec']['template']['spec']['containers'][0]['volumeMounts'] == \
               [{'mountPath': '/var/data/my-data', 'name': 'test-volume'}]

    mock_krogon_dsl(_run_dsl)


def test_deployment_can_set_deployment_volume_claim():
    def _run_dsl(args):
        os: MockOsSystem = args["os_system"]
        fs: MockFileSystem = args["file_system"]
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

        _, result = run_in_cluster(
            conn=gke_conn(cluster_name, project_id, service_account_b64),
            templates=[
                deployment(app_name)
                    .with_rolling_update(max_surge='20%', max_unavailable='20%')
                    .with_volume_claim(name='test-volume', claim_name='some-claim-name')
                    .with_container(container('test', 'test:100')
                                    .with_volume_mount('test-volume', '/var/data/my-data'))

            ]
        )
        deployment_yaml = find_write_template_calls(fs)[0]
        assert deployment_yaml['spec']['template']['spec']['volumes'] == [
            {'persistentVolumeClaim': {'claimName': 'some-claim-name'},
             'name': 'test-volume'}]
        assert deployment_yaml['spec']['template']['spec']['containers'][0]['volumeMounts'] == \
               [{'mountPath': '/var/data/my-data', 'name': 'test-volume'}]

    mock_krogon_dsl(_run_dsl)


def test_deployment_can_set_env_var_from_context():
    def _run_dsl(args):
        os: MockOsSystem = args["os_system"]
        fs: MockFileSystem = args["file_system"]
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

        _, result = run_in_cluster(
            conn=gke_conn(cluster_name, project_id, service_account_b64),
            templates=[
                deployment(app_name)
                    .with_rolling_update(max_surge='20%', max_unavailable='20%')
                    .with_volume_claim(name='test-volume', claim_name='some-claim-name')
                    .with_container(container('test', 'test:100')
                                    .with_volume_mount('test-volume', '/var/data/my-data')
                                    .with_environment_from_context('ENV', lambda c: c('cluster_name')))

            ]
        )
        deployment_yaml = find_write_template_calls(fs)[0]
        assert deployment_yaml['spec']['template']['spec']['containers'][0]['env'][1]['name'] == 'ENV'
        assert deployment_yaml['spec']['template']['spec']['containers'][0]['env'][1]['value'] == cluster_name

    mock_krogon_dsl(_run_dsl)


def test_deployment_can_set_init_containers():
    def _run_dsl(args):
        os: MockOsSystem = args["os_system"]
        fs: MockFileSystem = args["file_system"]
        project_id = "project1"
        app_name = 'test-service'
        cluster_name = 'prod-us-east1'
        kubectl_version = "v1.15.3"
        service_account_b64 = b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))
        init_container_1 = container(name='init-myservice', image='busybox:1.0')
        init_container_2 = container(name='init-myservice-2', image='busybox:2.0')

        os.mock_clusters_list([cluster_name])
        os.mock_kubernetes_release(E.success(kubectl_version))
        os.mock_download_install_kubectl(kubectl_version, E.success())
        os.mock_create_kube_config(cluster_name, E.success())
        os.mock_kubectl_apply_temp_file(cluster_name, E.success())

        _, result = run_in_cluster(
            conn=gke_conn(cluster_name, project_id, service_account_b64),
            templates=[
                deployment(app_name)
                    .with_rolling_update(max_surge='20%', max_unavailable='20%')
                    .with_volume_claim(name='test-volume', claim_name='some-claim-name')
                    .with_init_containers([init_container_1, init_container_2])
            ]
        )
        deployment_yaml = find_write_template_calls(fs)[0]
        init_containers = deployment_yaml['spec']['template']['spec']['initContainers']
        assert init_containers[0]['name'] == 'init-myservice-app'
        assert init_containers[0]['image'] == 'busybox:1.0'
        assert init_containers[1]['name'] == 'init-myservice-2-app'
        assert init_containers[1]['image'] == 'busybox:2.0'

    mock_krogon_dsl(_run_dsl)


def test_deployment_can_set_multiple_containers():
    def _run_dsl(args):
        os: MockOsSystem = args["os_system"]
        fs: MockFileSystem = args["file_system"]
        project_id = "project1"
        app_name = 'test-service'
        cluster_name = 'prod-us-east1'
        kubectl_version = "v1.15.3"
        service_account_b64 = b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))
        container_1 = container(name='myservice', image='busybox:1.0')
        container_2 = container(name='myservice-2', image='busybox:2.0')

        os.mock_clusters_list([cluster_name])
        os.mock_kubernetes_release(E.success(kubectl_version))
        os.mock_download_install_kubectl(kubectl_version, E.success())
        os.mock_create_kube_config(cluster_name, E.success())
        os.mock_kubectl_apply_temp_file(cluster_name, E.success())

        _, result = run_in_cluster(
            conn=gke_conn(cluster_name, project_id, service_account_b64),
            templates=[
                deployment(app_name)
                    .with_containers([container_1, container_2])
            ]
        )
        deployment_yaml = find_write_template_calls(fs)[0]
        containers = deployment_yaml['spec']['template']['spec']['containers']
        assert containers[0]['name'] == 'myservice-app'
        assert containers[0]['image'] == 'busybox:1.0'
        assert containers[1]['name'] == 'myservice-2-app'
        assert containers[1]['image'] == 'busybox:2.0'

    mock_krogon_dsl(_run_dsl)


def test_deployment_can_gen_template():
    def _run_dsl(args):
        os: MockOsSystem = args["os_system"]
        fs: MockFileSystem = args["file_system"]
        app_name = 'test-service'
        cluster_name = 'prod-us-east1'
        kubectl_version = "v1.15.3"
        container_1 = container(name='myservice', image='busybox:1.0')
        container_2 = container(name='myservice-2', image='busybox:2.0')

        os.mock_clusters_list([cluster_name])
        os.mock_kubernetes_release(E.success(kubectl_version))
        os.mock_download_install_kubectl(kubectl_version, E.success())
        os.mock_create_kube_config(cluster_name, E.success())
        os.mock_kubectl_apply_temp_file(cluster_name, E.success())

        _, result = gen_template([
            deployment(app_name)
                .with_containers([container_1, container_2])
        ])
        deployment_yaml = find_write_template_calls(fs)[0]
        containers = deployment_yaml['spec']['template']['spec']['containers']
        assert containers[0]['name'] == 'myservice-app'
        assert containers[0]['image'] == 'busybox:1.0'
        assert containers[1]['name'] == 'myservice-2-app'
        assert containers[1]['image'] == 'busybox:2.0'

    mock_krogon_dsl(_run_dsl)

