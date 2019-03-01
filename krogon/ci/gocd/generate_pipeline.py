import krogon.file_system as fs
import krogon.k8s.kubectl as k
import krogon.yaml as yaml
import krogon.either as E
import krogon.maybe as M
from krogon.nullable import nmap
from .gocd_api import request
from typing import Optional
from .encrypt_secret import encrypt_secret


def register_pipeline(k_ctl: k.KubeCtl,
                      app_name: str,
                      git_url: str,
                      username: str,
                      password: str,
                      cluster_name: str):

    return _delete_repo_registration(k_ctl, app_name, username, password, cluster_name) \
           | E.then | (lambda secret:  _register_repo(k_ctl, app_name, git_url, username, password, cluster_name))


def generate_pipeline(k_ctl: k.KubeCtl,
                      file: fs.FileSystem,
                      project_id: str,
                      service_account_b64: str,
                      app_name: str,
                      git_url: str,
                      krogon_agent_name: str,
                      krogon_file_path: str,
                      username: str,
                      password: str,
                      cluster_name: str):

    return encrypt_secret(k_ctl, service_account_b64, username, password, cluster_name) \
           | E.then | (lambda secret:  _generate_gocd_template(file, project_id, secret, app_name, git_url,
                                                               krogon_agent_name, krogon_file_path)) \
           | E.then | (lambda secret:  _delete_repo_registration(k_ctl, app_name, username, password, cluster_name)) \
           | E.then | (lambda secret:  _register_repo(k_ctl, app_name, git_url, username, password, cluster_name))


def _delete_repo_registration(k_ctl: k.KubeCtl,
                              app_name: str,
                              username: str,
                              password: str,
                              cluster_name: str):

    return request(k_ctl, 'DELETE', '/go/api/admin/config_repos/' + app_name,
                   {'Accept': 'application/vnd.go.cd.v1+json'},
                   None,
                   username, password, cluster_name) \
           | E.catch_error | (lambda _: E.Success())


def _register_repo(k_ctl: k.KubeCtl,
                   app_name: str,
                   git_url: str,
                   username: str,
                   password: str,
                   cluster_name: str):

    payload = {
        "id": app_name,
        "plugin_id": "yaml.config.plugin",
        "material": {
            "type": "git",
            "attributes": {
                "url": git_url,
                "branch": "master",
                "auto_update": True
            }
        }
    }

    return request(k_ctl, 'POST', '/go/api/admin/config_repos',
                   {'Accept': 'application/vnd.go.cd.v1+json'},
                   payload,
                   username, password, cluster_name)


def _generate_gocd_template(file: fs.FileSystem,
                            project_id: str,
                            secure_service_account_b64: str,
                            app_name: str,
                            git_url: str,
                            krogon_agent_name: str,
                            krogon_file_path: str):

    image_url = 'gcr.io/{}/{}:${{GO_PIPELINE_LABEL}}'.format(project_id, app_name)
    gocd_template = _create_gocd_yaml_template(app_name, git_url, image_url,
                                               krogon_agent_name, krogon_file_path,
                                               project_id, secure_service_account_b64)

    file.write(file.cwd() + '/ci.gocd.yaml', yaml.dump(gocd_template))
    return  E.Success()


def _create_gocd_yaml_template(app_name: str, git_url: str, image_url: str,
                               krogon_agent_name: str, krogon_file_path: str,
                               project_id: str, secure_service_account_b64: str):

    build_pipeline = app_name + '-BuildAndPublishArtifact'
    deploy_pipeline = app_name + '-DeployArtifact'

    return {
        'format_version': '3',
        'environments': {
            'prod': {
                'pipelines': [build_pipeline, deploy_pipeline]
            }
        },
        'pipelines': {
            build_pipeline:
                _create_pipeline_template(
                    group=app_name,
                    git_url=git_url,
                    stage=_create_stage_with_job(
                        'BuildAndPublish',
                        _create_build_image_job(image_url))),

            deploy_pipeline:
                _create_pipeline_template(
                    group=app_name,
                    git_url=git_url,
                    stage=_create_stage_with_job(
                        'Deploy',
                        _create_krogon_job(krogon_agent_name,
                                           krogon_file_path, project_id,
                                           secure_service_account_b64,
                                           version='${GO_DEPENDENCY_LABEL_UPSTREAMJOB}')),
                    upstream_pipeline=build_pipeline,
                    upstream_stage='BuildAndPublish')
        }
    }


def _create_pipeline_template(group: str, git_url: str, stage: dict,
                              upstream_pipeline: Optional[str] = None,
                              upstream_stage: Optional[str] = None):

    upstream = M.Just({'pipeline': upstream_pipeline, 'stage': upstream_stage}) \
        if upstream_pipeline is not None and upstream_stage is not None \
        else M.Nothing()

    return {
        'group': group,
        'label_template': '1.0.${COUNT}',
        'materials': nmap({
            'git_repo': {
                'git': git_url,
                'branch': 'master'
            }
        }).append_if_value('UpstreamJob', upstream).to_map(),
        'stages': [stage]
    }


def _create_stage_with_job(stage_name: str, job: dict):
    return {stage_name: {
        'jobs': {'Run'+stage_name: job}
    }}


def _create_build_image_job(image_url: str):
    return {
        'elastic_profile_id': 'gocd-agent-default',
        'tasks': [
            {'exec': {
                'command': 'sh',
                'arguments': ['-c', 'docker build -t '+image_url+' --build-arg ssh_prv_key="$(cat ~/.ssh/id_rsa)"'
                                                                 ' --build-arg ssh_pub_key="$(cat ~/.ssh/id_rsa.pub)" .']
            }},
            {'script': 'curl -fsSL "https://github.com/GoogleCloudPlatform/docker-credential-gcr' +
                       '/releases/download/v1.5.0/docker-credential-gcr_linux_amd64-1.5.0.tar.gz"' +
                       ' | tar xz --to-stdout ./docker-credential-gcr > /home/go/docker-credential-gcr ' +
                       '&& chmod +x /home/go/docker-credential-gcr ' +
                       '&& export PATH=$PATH:/home/go ' +
                       '&& /home/go/docker-credential-gcr configure-docker ' +
                       '&& docker push '+image_url
             }
        ]
    }


def _create_krogon_job(krogon_agent_name: str,
                       krogon_file_path: str,
                       project_id: str,
                       secure_service_account_b64: str,
                       version: str):

    return {
        'elastic_profile_id': krogon_agent_name,
        'environment_variables': {'GCP_PROJECT': project_id},
        'secure_variables': {'GCP_SERVICE_ACCOUNT_B64': secure_service_account_b64},
        'tasks': [
            {'exec': {
                'command': 'sh',
                'arguments': ['VERSION='+version+' python '+krogon_file_path]
            }}
        ]
    }


def _create_test_job(agent_type: str):
    cmd = {
        'gocd-agent-node': {
            'command': 'npm',
            'arguments': ['test']
        },
        'gocd-agent-elixir': {
            'command': 'mix',
            'arguments': ['test']
        },
        'gocd-agent-python': {
            'command': 'pytest',
        }
    }[agent_type]

    return {
        'elastic_profile_id': agent_type,
        'tasks': [
            {'exec': {
                'command': cmd['command'],
                'arguments': cmd['arguments']
            }}
        ]
    }

