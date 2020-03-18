from python_mock import assert_that, MatchArg

import krogon.either as E
import json
from krogon import run_in_cluster, gke_conn, gen_template
from krogon.k8s import micro_service, container
from tests.helpers.mock_file_system import MockFileSystem, find_write_template_calls
from tests.helpers.mock_os_system import MockOsSystem
from base64 import b64encode
from tests.helpers.entry_mocks import mock_krogon_dsl


def test_micro_service_can_generate_micro_service_template():
    def _run_dsl(args):
        os: MockOsSystem = args["os_system"]
        fs: MockFileSystem = args["file_system"]
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

        _, result = run_in_cluster(
            conn=gke_conn(cluster_name, project_id, service_account_b64),
            templates=[
                micro_service(service_name, image_url, app_port)
            ]
        )
        yamls = find_write_template_calls(fs)
        assert yamls[0]['kind'] == 'Service'
        assert yamls[0]['metadata']['name'] == service_name
        assert yamls[0]['spec']['selector']['app'] == service_name+'-app'
        assert yamls[0]['spec']['ports'][0]['targetPort'] == app_port
        assert yamls[0]['spec']['ports'][0]['port'] == service_port

        assert yamls[1]['kind'] == 'Deployment'

    mock_krogon_dsl(_run_dsl)


def test_micro_service_can_set_secret():
    def _run_dsl(args):
        os: MockOsSystem = args["os_system"]
        fs: MockFileSystem = args["file_system"]
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

        _, result = run_in_cluster(
            conn=gke_conn(cluster_name, project_id, service_account_b64),
            templates=[
                micro_service(service_name, image_url, app_port)
                    .with_environment_secret('coolSecret', {'ENV_NAME': 'secretkey'})
            ]
        )
        yamls = find_write_template_calls(fs)
        assert yamls[1]['kind'] == 'Deployment'
        container = yamls[1]['spec']['template']['spec']['containers'][0]
        assert container['env'][0]['name'] == 'ENV_NAME'
        assert container['env'][0]['valueFrom']['secretKeyRef']['name'] == 'coolSecret'
        assert container['env'][0]['valueFrom']['secretKeyRef']['key'] == 'secretkey'

    mock_krogon_dsl(_run_dsl)


def test_micro_service_can_change_service_type():
    def _run_dsl(args):
        fs: MockFileSystem = args["file_system"]
        service_type = 'NodePort'
        cluster_name = 'prod-us-east1'
        project_id = 'project1'
        service_account_b64 = b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))

        _, result = run_in_cluster(
            conn=gke_conn(cluster_name, project_id, service_account_b64),
            templates=[
                micro_service('test', "test-service:1.0.0", 3000)
                    .with_service_type(service_type)
            ]
        )
        yamls = find_write_template_calls(fs)
        assert yamls[0]['kind'] == 'Service'
        assert yamls[0]['spec']['type'] == 'NodePort'

    mock_krogon_dsl(_run_dsl)


def test_micro_service_can_set_cpu_request():
    def _run_dsl(args):
        fs: MockFileSystem = args["file_system"]
        service_type = 'NodePort'
        cluster_name = 'prod-us-east1'
        project_id = 'project1'
        service_account_b64 = b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))

        _, result = run_in_cluster(
            conn=gke_conn(cluster_name, project_id, service_account_b64),
            templates=[
                micro_service('test', "test-service:1.0.0", 3000)
                    .with_service_type(service_type)
                    .with_resources(cpu_request="1")
            ]
        )
        yamls = find_write_template_calls(fs)
        assert yamls[1]['kind'] == 'Deployment'
        container = yamls[1]['spec']['template']['spec']['containers'][0]
        assert container['resources'] == {'requests': {'cpu': '1'}}

    mock_krogon_dsl(_run_dsl)


def test_micro_service_can_set_resources():
    def _run_dsl(args):
        fs: MockFileSystem = args["file_system"]
        service_type = 'NodePort'
        cluster_name = 'prod-us-east1'
        project_id = 'project1'
        service_account_b64 = b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))

        _, result = run_in_cluster(
            conn=gke_conn(cluster_name, project_id, service_account_b64),
            templates=[
                micro_service('test', "test-service:1.0.0", 3000)
                    .with_service_type(service_type)
                    .with_resources(cpu_request="1",
                                    memory_request="64Mi",
                                    cpu_limit="2",
                                    memory_limit="128Mi")
            ]
        )
        yamls = find_write_template_calls(fs)
        assert yamls[1]['kind'] == 'Deployment'
        container = yamls[1]['spec']['template']['spec']['containers'][0]
        assert container['resources'] == {'requests': {'cpu': '1', 'memory': '64Mi'},
                                          'limits': {'cpu': '2', 'memory': '128Mi'}}

    mock_krogon_dsl(_run_dsl)


def test_micro_service_can_deploy_a_micro_service_side_car():
    def _run_dsl(args):
        fs: MockFileSystem = args["file_system"]
        cluster_name = 'prod-us-east1'
        project_id = 'project1'
        service_account_b64 = b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))

        _, result = run_in_cluster(
            conn=gke_conn(cluster_name, project_id, service_account_b64),
            templates=[
                micro_service('test', "test-service:1.0.0", 3000)
                    .with_sidecar(container('my-sidecar', 'my-sidecar:1.0.0'))
            ]
        )
        yamls = find_write_template_calls(fs)
        assert yamls[1]['kind'] == 'Deployment'
        sidecar = yamls[1]['spec']['template']['spec']['containers'][1]
        assert sidecar['name'] == 'my-sidecar-app'
        assert sidecar['image'] == 'my-sidecar:1.0.0'

    mock_krogon_dsl(_run_dsl)


def test_micro_service_can_deploy_setup_volume_mounts():
    def _run_dsl(args):
        fs: MockFileSystem = args["file_system"]
        cluster_name = 'prod-us-east1'
        project_id = 'project1'
        service_account_b64 = b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))

        _, result = run_in_cluster(
            conn=gke_conn(cluster_name, project_id, service_account_b64),
            templates=[
                micro_service('test', "test-service:1.0.0", 3000)
                    .with_empty_volume('my-volume', '/var/data/my-data')
                    .with_sidecar(container('my-sidecar', 'my-sidecar:1.0.0')
                                  .with_volume_mount('my-volume', 'var/data/sidecar-data'))
            ]
        )
        deployment = find_write_template_calls(fs)[1]
        assert deployment['spec']['template']['spec']['volumes'][0] == {'name': 'my-volume', 'emptyDir': {}}
        microservice = deployment['spec']['template']['spec']['containers'][0]
        assert microservice['volumeMounts'][0] == {'name': 'my-volume', 'mountPath': '/var/data/my-data'}
        sidecar = deployment['spec']['template']['spec']['containers'][1]
        assert sidecar['volumeMounts'][0] == {'name': 'my-volume', 'mountPath': 'var/data/sidecar-data'}

    mock_krogon_dsl(_run_dsl)


def test_micro_service_pick_clusters_using_regex():
    def _run_dsl(args):
        fs: MockFileSystem = args['file_system']
        os: MockOsSystem = args["os_system"]
        os.mock_clusters_list(['prod-us-east1-api-cluster', 'prod-10-api-cluster', 'stage-10-api-cluster'])
        cluster_name = 'prod-.*-api-cluster'
        project_id = 'project1'
        service_account_b64 = b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))

        _, result = run_in_cluster(
            conn=gke_conn(cluster_name, project_id, service_account_b64),
            templates=[
                micro_service('test', "test-service:1.0.0", 3000)
                    .with_empty_volume('my-volume', '/var/data/my-data')
                    .with_sidecar(container('my-sidecar', 'my-sidecar:1.0.0')
                                  .with_volume_mount('my-volume', 'var/data/sidecar-data'))
            ]
        )

        assert 'prod-us-east1-api-cluster' in find_cluster_templates(fs)
        assert 'prod-10-api-cluster' in find_cluster_templates(fs)
        assert 'stage-10-api-cluster' not in find_cluster_templates(fs)

    mock_krogon_dsl(_run_dsl)


def test_micro_service_can_ensure_one_pod_at_a_time():
    def _run_dsl(args):
        fs: MockFileSystem = args['file_system']
        cluster_name = 'prod-us-east1'
        project_id = 'project1'
        service_account_b64 = b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))

        _, result = run_in_cluster(
            conn=gke_conn(cluster_name, project_id, service_account_b64),
            templates=[
                micro_service('test', "test-service:1.0.0", 3000)
                    .with_ensure_only_one()
                    .with_empty_volume('my-volume', '/var/data/my-data')
                    .with_sidecar(container('my-sidecar', 'my-sidecar:1.0.0')
                                  .with_volume_mount('my-volume', 'var/data/sidecar-data'))
            ]
        )
        deployment = find_write_template_calls(fs)[1]
        assert deployment['spec']['replicas'] == 1
        assert deployment['spec']['strategy'] == {'type': 'Recreate'}
        hpa = find_write_template_calls(fs)[2]
        assert hpa['spec']['minReplicas'] == 1
        assert hpa['spec']['maxReplicas'] == 1

    mock_krogon_dsl(_run_dsl)


def test_micro_service_can_set_hpa():
    def _run_dsl(args):
        fs: MockFileSystem = args['file_system']
        cluster_name = 'prod-us-east1'
        project_id = 'project1'
        service_account_b64 = b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))

        _, result = run_in_cluster(
            conn=gke_conn(cluster_name, project_id, service_account_b64),
            templates=[
                micro_service('test', "test-service:1.0.0", 3000)
                    .with_replicas(min=5, max=10)
                    .with_empty_volume('my-volume', '/var/data/my-data')
                    .with_sidecar(container('my-sidecar', 'my-sidecar:1.0.0')
                                  .with_volume_mount('my-volume', 'var/data/sidecar-data'))
            ]
        )
        deployment = find_write_template_calls(fs)[1]
        assert deployment['spec']['replicas'] == 5
        hpa = find_write_template_calls(fs)[2]
        assert hpa['spec']['minReplicas'] == 5
        assert hpa['spec']['maxReplicas'] == 10

    mock_krogon_dsl(_run_dsl)


def test_micro_service_can_ensure_cpu_scale_up_threshold():
    def _run_dsl(args):
        fs: MockFileSystem = args['file_system']
        cluster_name = 'prod-us-east1'
        project_id = 'project1'
        service_account_b64 = b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))

        _, result = run_in_cluster(
            conn=gke_conn(cluster_name, project_id, service_account_b64),
            templates=[
                micro_service('test', "test-service:1.0.0", 3000)
                    .with_replicas(min=5, max=10, cpu_threshold_percentage=80)
                    .with_empty_volume('my-volume', '/var/data/my-data')
                    .with_sidecar(container('my-sidecar', 'my-sidecar:1.0.0')
                                  .with_volume_mount('my-volume', 'var/data/sidecar-data'))
            ]
        )
        deployment = find_write_template_calls(fs)[1]
        assert deployment['spec']['replicas'] == 5
        hpa = find_write_template_calls(fs)[2]
        assert hpa['spec']['minReplicas'] == 5
        assert hpa['spec']['maxReplicas'] == 10
        assert hpa['spec']['targetCPUUtilizationPercentage'] == 80

    mock_krogon_dsl(_run_dsl)


def test_micro_service_can_set_rolling_update():
    def _run_dsl(args):
        fs: MockFileSystem = args['file_system']
        cluster_name = 'prod-us-east1'
        project_id = 'project1'
        service_account_b64 = b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))

        _, result = run_in_cluster(
            conn=gke_conn(cluster_name, project_id, service_account_b64),
            templates=[
                micro_service('test', "test-service:1.0.0", 3000)
                    .with_rolling_update(max_surge='20%', max_unavailable='20%')
                    .with_empty_volume('my-volume', '/var/data/my-data')
                    .with_sidecar(container('my-sidecar', 'my-sidecar:1.0.0')
                                  .with_volume_mount('my-volume', 'var/data/sidecar-data'))
            ]
        )
        deployment = find_write_template_calls(fs)[1]
        assert deployment['spec']['strategy'] == {'rollingUpdate': {'maxSurge': '20%', 'maxUnavailable': '20%'},
                                                  'type': 'RollingUpdate'}

    mock_krogon_dsl(_run_dsl)


def test_micro_service_can_set_annotations():
    def _run_dsl(args):
        fs: MockFileSystem = args['file_system']
        cluster_name = 'prod-us-east1'
        project_id = 'project1'
        service_account_b64 = b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))

        _, result = run_in_cluster(
            conn=gke_conn(cluster_name, project_id, service_account_b64),
            templates=[
                micro_service('test', "test-service:1.0.0", 3000)
                    .with_annotations({'some': 'thing'})
                    .with_empty_volume('my-volume', '/var/data/my-data')
                    .with_sidecar(container('my-sidecar', 'my-sidecar:1.0.0')
                                  .with_volume_mount('my-volume', 'var/data/sidecar-data'))
            ]
        )
        deployment = find_write_template_calls(fs)[1]
        assert deployment['spec']['template']['metadata']['annotations'] == {'some': 'thing'}

    mock_krogon_dsl(_run_dsl)


def test_micro_service_can_setup_volume_claims():
    def _run_dsl(args):
        fs: MockFileSystem = args['file_system']
        cluster_name = 'prod-us-east1'
        project_id = 'project1'
        service_account_b64 = b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))

        _, result = run_in_cluster(
            conn=gke_conn(cluster_name, project_id, service_account_b64),
            templates=[
                micro_service('test', "test-service:1.0.0", 3000)
                    .with_volume_claim('my-volume', 'some-volume-claim', '/var/data/my-data')
                    .with_sidecar(container('my-sidecar', 'my-sidecar:1.0.0')
                                  .with_volume_mount('my-volume', 'var/data/sidecar-data'))
            ]
        )
        deployment = find_write_template_calls(fs)[1]
        assert deployment['spec']['template']['spec']['volumes'][0] == {
            'name': 'my-volume',
            'persistentVolumeClaim': {'claimName': 'some-volume-claim'}}
        microservice = deployment['spec']['template']['spec']['containers'][0]
        assert microservice['volumeMounts'][0] == {'name': 'my-volume', 'mountPath': '/var/data/my-data'}
        sidecar = deployment['spec']['template']['spec']['containers'][1]
        assert sidecar['volumeMounts'][0] == {'name': 'my-volume', 'mountPath': 'var/data/sidecar-data'}

    mock_krogon_dsl(_run_dsl)


def test_micro_service_can_set_env_var_from_context_on_sidecar():
    def _run_dsl(args):
        fs: MockFileSystem = args['file_system']
        cluster_name = 'prod-us-east1'
        project_id = 'project1'
        service_account_b64 = b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))

        _, result = run_in_cluster(
            conn=gke_conn(cluster_name, project_id, service_account_b64),
            templates=[
                micro_service('test', "test-service:1.0.0", 3000)
                    .with_sidecar(container('my-sidecar', 'my-sidecar:1.0.0')
                                  .with_volume_mount('my-volume', 'var/data/sidecar-data')
                                  .with_environment_from_context('ENV', lambda c: c('cluster_name')))
            ]
        )
        deployment = find_write_template_calls(fs)[1]
        microservice = deployment['spec']['template']['spec']['containers'][1]
        assert microservice['env'][1]['name'] == 'ENV'
        assert microservice['env'][1]['value'] == 'prod-us-east1'

    mock_krogon_dsl(_run_dsl)


def test_micro_service_can_set_init_containers():
    init_container_1 = {'name': 'init-myservice', 'image': 'busybox:1.0'}
    init_container_2 = {'name': 'init-myservice-2', 'image': 'busybox:2.0'}
    cluster_name = 'prod-us-east1'
    project_id = "project1"
    service_account_b64 = b64encode(json.dumps({'key': 'someKey'}).encode('utf-8'))

    def _run_dsl(args):
        fs: MockFileSystem = args['file_system']
        _, result = run_in_cluster(
            conn=gke_conn(cluster_name, project_id, service_account_b64),
            templates=[
                micro_service('test', "test-service:1.0.0", 3000)
                    .with_init_containers([init_container_1, init_container_2])
            ]
        )
        deployment = find_write_template_calls(fs)[1]
        init_containers = deployment['spec']['template']['spec']['initContainers']
        assert init_containers[0]['name'] == 'init-myservice'
        assert init_containers[0]['image'] == 'busybox:1.0'
        assert init_containers[1]['name'] == 'init-myservice-2'
        assert init_containers[1]['image'] == 'busybox:2.0'

    mock_krogon_dsl(_run_dsl)


def test_micro_service_can_gen_template():
    def _run_dsl(args):
        fs: MockFileSystem = args['file_system']
        _, result = gen_template([
            micro_service('test', "test-service:1.0.0", 3000)
                .with_replicas(min=5, max=10, cpu_threshold_percentage=80)
        ])
        deployment = find_write_template_calls(fs)[1]
        assert deployment['spec']['replicas'] == 5
        hpa = find_write_template_calls(fs)[2]
        assert hpa['spec']['minReplicas'] == 5
        assert hpa['spec']['maxReplicas'] == 10

    mock_krogon_dsl(_run_dsl)


def find_cluster_templates(fs):
    yamls = find_write_template_calls(fs)
    cluster_envs = []
    for yml in yamls:
        if 'template' in yml['spec']:
            cluster_envs.append(yml['spec']['template']['spec']['containers'][0]['env'][0]['value'])
    return cluster_envs


