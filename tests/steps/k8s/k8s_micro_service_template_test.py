from python_mock import PyMock, assert_that, MatchArg

import krogon.either as E
import json
from krogon import krogon
from krogon import config
from krogon.steps.k8s import run_in_cluster, micro_service, container
from tests.helpers.mock_file_system import MockFileSystem
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
        assert result[0][0].templates[0]['kind'] == 'Service'
        assert result[0][0].templates[0]['metadata']['name'] == service_name
        assert result[0][0].templates[0]['spec']['selector']['app'] == service_name+'-app'
        assert result[0][0].templates[0]['spec']['ports'][0]['targetPort'] == app_port
        assert result[0][0].templates[0]['spec']['ports'][0]['port'] == service_port

        assert result[0][0].templates[1]['kind'] == 'Deployment'

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
        assert result[0][0].templates[1]['kind'] == 'Deployment'
        container = result[0][0].templates[1]['spec']['template']['spec']['containers'][0]
        assert container['env'][0]['name'] == 'ENV_NAME'
        assert container['env'][0]['valueFrom']['secretKeyRef']['name'] == 'coolSecret'
        assert container['env'][0]['valueFrom']['secretKeyRef']['key'] == 'secretkey'

    mock_krogon_dsl(_run_dsl)


def test_can_change_service_type():
    def _run_dsl(args):
        service_type = 'NodePort'

        _, result = krogon(
            run_steps=[
                run_in_cluster(
                    named='prod-us-east1',
                    templates=[
                        micro_service('test', "test-service:1.0.0", 3000)
                            .with_service_type(service_type)
                    ]
                )
            ],
            for_config=config("project1",
                              b64encode(json.dumps({'key': 'someKey'}).encode('utf-8')),
                              output_template=True)
        )
        assert result[0][0].templates[0]['kind'] == 'Service'
        assert result[0][0].templates[0]['spec']['type'] == 'NodePort'

    mock_krogon_dsl(_run_dsl)


def test_can_set_cpu_request():
    def _run_dsl(args):
        service_type = 'NodePort'

        _, result = krogon(
            run_steps=[
                run_in_cluster(
                    named='prod-us-east1',
                    templates=[
                        micro_service('test', "test-service:1.0.0", 3000)
                            .with_service_type(service_type)
                            .with_resources(cpu_request="1")
                    ]
                )
            ],
            for_config=config("project1",
                              b64encode(json.dumps({'key': 'someKey'}).encode('utf-8')),
                              output_template=True)
        )
        assert result[0][0].templates[1]['kind'] == 'Deployment'
        container = result[0][0].templates[1]['spec']['template']['spec']['containers'][0]
        assert container['resources'] == {'requests': {'cpu': '1'}}

    mock_krogon_dsl(_run_dsl)


def test_can_set_resources():
    def _run_dsl(args):
        service_type = 'NodePort'

        _, result = krogon(
            run_steps=[
                run_in_cluster(
                    named='prod-us-east1',
                    templates=[
                        micro_service('test', "test-service:1.0.0", 3000)
                            .with_service_type(service_type)
                            .with_resources(cpu_request="1",
                                            memory_request="64Mi",
                                            cpu_limit="2",
                                            memory_limit="128Mi")
                    ]
                )
            ],
            for_config=config("project1",
                              b64encode(json.dumps({'key': 'someKey'}).encode('utf-8')),
                              output_template=True)
        )
        assert result[0][0].templates[1]['kind'] == 'Deployment'
        container = result[0][0].templates[1]['spec']['template']['spec']['containers'][0]
        assert container['resources'] == {'requests': {'cpu': '1', 'memory': '64Mi'},
                                          'limits': {'cpu': '2', 'memory': '128Mi'}}

    mock_krogon_dsl(_run_dsl)


def test_can_deploy_a_micro_service_side_car():
    def _run_dsl(args):
        _, result = krogon(
            run_steps=[
                run_in_cluster(
                    named='prod-us-east1',
                    templates=[
                        micro_service('test', "test-service:1.0.0", 3000)
                        .with_sidecar(container('my-sidecar', 'my-sidecar:1.0.0'))
                    ]
                )
            ],
            for_config=config("project1",
                              b64encode(json.dumps({'key': 'someKey'}).encode('utf-8')),
                              output_template=True)
        )
        assert result[0][0].templates[1]['kind'] == 'Deployment'
        sidecar = result[0][0].templates[1]['spec']['template']['spec']['containers'][1]
        assert sidecar['name'] == 'my-sidecar-app'
        assert sidecar['image'] == 'my-sidecar:1.0.0'

    mock_krogon_dsl(_run_dsl)


def test_can_deploy_setup_volume_mounts():
    def _run_dsl(args):
        _, result = krogon(
            run_steps=[
                run_in_cluster(
                    named='prod-us-east1',
                    templates=[
                        micro_service('test', "test-service:1.0.0", 3000)
                            .with_empty_volume('my-volume', '/var/data/my-data')
                            .with_sidecar(container('my-sidecar', 'my-sidecar:1.0.0')
                                          .with_volume_mount('my-volume', 'var/data/sidecar-data'))
                    ]
                )
            ],
            for_config=config("project1",
                              b64encode(json.dumps({'key': 'someKey'}).encode('utf-8')),
                              output_template=True)
        )
        deployment = result[0][0].templates[1]
        assert deployment['spec']['template']['spec']['volumes'][0] == {'name': 'my-volume', 'emptyDir': {}}
        microservice = deployment['spec']['template']['spec']['containers'][0]
        assert microservice['volumeMounts'][0] == {'name': 'my-volume', 'mountPath': '/var/data/my-data'}
        sidecar = deployment['spec']['template']['spec']['containers'][1]
        assert sidecar['volumeMounts'][0] == {'name': 'my-volume', 'mountPath': 'var/data/sidecar-data'}

    mock_krogon_dsl(_run_dsl)


def test_pick_clusters_using_regex():
    def _run_dsl(args):
        file: MockFileSystem = args['file_system']
        os: MockOsSystem = args["os_system"]
        os.mock_clusters_list(['prod-us-east1-api-cluster', 'prod-10-api-cluster', 'stage-10-api-cluster'])

        _, result = krogon(
            run_steps=[
                run_in_cluster(
                    named='prod-.*-api-cluster',
                    templates=[
                        micro_service('test', "test-service:1.0.0", 3000)
                            .with_empty_volume('my-volume', '/var/data/my-data')
                            .with_sidecar(container('my-sidecar', 'my-sidecar:1.0.0')
                                          .with_volume_mount('my-volume', 'var/data/sidecar-data'))
                    ]
                )
            ],
            for_config=config("project1",
                              b64encode(json.dumps({'key': 'someKey'}).encode('utf-8')),
                              output_template=True)
        )

        assert_that(file.file_system.write).was_called(
            with_args=[MockFileSystem.cwd()+'/output/prod-us-east1-api-cluster/k8s.yaml', MatchArg.any()])
        assert_that(file.file_system.write).was_called(
            with_args=[MockFileSystem.cwd()+'/output/prod-10-api-cluster/k8s.yaml', MatchArg.any()])
        assert_that(file.file_system.write).was_not_called(
            with_args=[MockFileSystem.cwd()+'/output/stage-10-api-cluster/k8s.yaml', MatchArg.any()])

    mock_krogon_dsl(_run_dsl)


def test_can_ensure_one_pod_at_a_time():
    def _run_dsl(args):
        _, result = krogon(
            run_steps=[
                run_in_cluster(
                    named='prod-us-east1',
                    templates=[
                        micro_service('test', "test-service:1.0.0", 3000)
                            .with_ensure_only_one()
                            .with_empty_volume('my-volume', '/var/data/my-data')
                            .with_sidecar(container('my-sidecar', 'my-sidecar:1.0.0')
                                          .with_volume_mount('my-volume', 'var/data/sidecar-data'))
                    ]
                )
            ],
            for_config=config("project1",
                              b64encode(json.dumps({'key': 'someKey'}).encode('utf-8')),
                              output_template=True)
        )
        deployment = result[0][0].templates[1]
        assert deployment['spec']['replicas'] == 1
        assert deployment['spec']['strategy'] == {'type': 'Recreate'}
        hpa = result[0][0].templates[2]
        assert hpa['spec']['minReplicas'] == 1
        assert hpa['spec']['maxReplicas'] == 1

    mock_krogon_dsl(_run_dsl)


def test_can_set_hpa():
    def _run_dsl(args):
        _, result = krogon(
            run_steps=[
                run_in_cluster(
                    named='prod-us-east1',
                    templates=[
                        micro_service('test', "test-service:1.0.0", 3000)
                            .with_replicas(min=5, max=10)
                            .with_empty_volume('my-volume', '/var/data/my-data')
                            .with_sidecar(container('my-sidecar', 'my-sidecar:1.0.0')
                                          .with_volume_mount('my-volume', 'var/data/sidecar-data'))
                    ]
                )
            ],
            for_config=config("project1",
                              b64encode(json.dumps({'key': 'someKey'}).encode('utf-8')),
                              output_template=True)
        )
        deployment = result[0][0].templates[1]
        assert deployment['spec']['replicas'] == 5
        hpa = result[0][0].templates[2]
        assert hpa['spec']['minReplicas'] == 5
        assert hpa['spec']['maxReplicas'] == 10

    mock_krogon_dsl(_run_dsl)


def test_can_ensure_cpu_scale_up_threshold():
    def _run_dsl(args):
        _, result = krogon(
            run_steps=[
                run_in_cluster(
                    named='prod-us-east1',
                    templates=[
                        micro_service('test', "test-service:1.0.0", 3000)
                            .with_replicas(min=5, max=10, cpu_threshold_percentage=80)
                            .with_empty_volume('my-volume', '/var/data/my-data')
                            .with_sidecar(container('my-sidecar', 'my-sidecar:1.0.0')
                                          .with_volume_mount('my-volume', 'var/data/sidecar-data'))
                    ]
                )
            ],
            for_config=config("project1",
                              b64encode(json.dumps({'key': 'someKey'}).encode('utf-8')),
                              output_template=True)
        )
        deployment = result[0][0].templates[1]
        assert deployment['spec']['replicas'] == 5
        hpa = result[0][0].templates[2]
        assert hpa['spec']['minReplicas'] == 5
        assert hpa['spec']['maxReplicas'] == 10
        assert hpa['spec']['targetCPUUtilizationPercentage'] == 80

    mock_krogon_dsl(_run_dsl)


def test_can_set_rolling_update():
    def _run_dsl(args):
        _, result = krogon(
            run_steps=[
                run_in_cluster(
                    named='prod-us-east1',
                    templates=[
                        micro_service('test', "test-service:1.0.0", 3000)
                            .with_rolling_update(max_surge='20%', max_unavailable='20%')
                            .with_empty_volume('my-volume', '/var/data/my-data')
                            .with_sidecar(container('my-sidecar', 'my-sidecar:1.0.0')
                                          .with_volume_mount('my-volume', 'var/data/sidecar-data'))
                    ]
                )
            ],
            for_config=config("project1",
                              b64encode(json.dumps({'key': 'someKey'}).encode('utf-8')),
                              output_template=True)
        )
        deployment = result[0][0].templates[1]
        assert deployment['spec']['strategy'] == {'rollingUpdate': {'maxSurge': '20%', 'maxUnavailable': '20%'},
                                                  'type': 'RollingUpdate'}

    mock_krogon_dsl(_run_dsl)


def test_can_set_annotations():
    def _run_dsl(args):
        _, result = krogon(
            run_steps=[
                run_in_cluster(
                    named='prod-us-east1',
                    templates=[
                        micro_service('test', "test-service:1.0.0", 3000)
                            .with_annotations({'some': 'thing'})
                            .with_empty_volume('my-volume', '/var/data/my-data')
                            .with_sidecar(container('my-sidecar', 'my-sidecar:1.0.0')
                                          .with_volume_mount('my-volume', 'var/data/sidecar-data'))
                    ]
                )
            ],
            for_config=config("project1",
                              b64encode(json.dumps({'key': 'someKey'}).encode('utf-8')),
                              output_template=True)
        )
        deployment = result[0][0].templates[1]
        assert deployment['spec']['template']['metadata']['annotations'] == {'some': 'thing'}

    mock_krogon_dsl(_run_dsl)


def test_can_setup_volume_claims():
    def _run_dsl(args):
        _, result = krogon(
            run_steps=[
                run_in_cluster(
                    named='prod-us-east1',
                    templates=[
                        micro_service('test', "test-service:1.0.0", 3000)
                            .with_volume_claim('my-volume', 'some-volume-claim', '/var/data/my-data')
                            .with_sidecar(container('my-sidecar', 'my-sidecar:1.0.0')
                                          .with_volume_mount('my-volume', 'var/data/sidecar-data'))
                    ]
                )
            ],
            for_config=config("project1",
                              b64encode(json.dumps({'key': 'someKey'}).encode('utf-8')),
                              output_template=True)
        )
        deployment = result[0][0].templates[1]
        assert deployment['spec']['template']['spec']['volumes'][0] == {
            'name': 'my-volume',
            'persistentVolumeClaim': {'claimName': 'some-volume-claim'}}
        microservice = deployment['spec']['template']['spec']['containers'][0]
        assert microservice['volumeMounts'][0] == {'name': 'my-volume', 'mountPath': '/var/data/my-data'}
        sidecar = deployment['spec']['template']['spec']['containers'][1]
        assert sidecar['volumeMounts'][0] == {'name': 'my-volume', 'mountPath': 'var/data/sidecar-data'}

    mock_krogon_dsl(_run_dsl)


def test_can_set_env_var_from_context_on_sidecar():
    def _run_dsl(args):
        _, result = krogon(
            run_steps=[
                run_in_cluster(
                    named='prod-us-east1',
                    templates=[
                        micro_service('test', "test-service:1.0.0", 3000)
                            .with_sidecar(container('my-sidecar', 'my-sidecar:1.0.0')
                                          .with_volume_mount('my-volume', 'var/data/sidecar-data')
                                          .with_environment_from_context('ENV', lambda c: c('cluster_name')))
                    ]
                )
            ],
            for_config=config("project1",
                              b64encode(json.dumps({'key': 'someKey'}).encode('utf-8')),
                              output_template=True)
        )
        deployment = result[0][0].templates[1]
        microservice = deployment['spec']['template']['spec']['containers'][1]
        assert microservice['env'][1]['name'] == 'ENV'
        assert microservice['env'][1]['value'] == 'prod-us-east1'

    mock_krogon_dsl(_run_dsl)


