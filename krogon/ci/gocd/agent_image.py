import krogon.file_system as fs
import krogon.k8s.kubectl as k
import krogon.yaml as yaml
import krogon.either as E
from . import gocd_version
from .gocd_api import request


def generate_agent_template(file: fs.FileSystem, agent_name: str, agent_folder: str, image_url: str):

    agent_pod_template = generate_agent_pod_template(agent_name, image_url)
    file.write(file.path_rel_to_cwd(agent_folder) + '/gocd-agent.yaml', yaml.dump(agent_pod_template))

    empty_docker_template = 'FROM gocd/gocd-agent-ubuntu-18.04:v' + gocd_version
    file.write(file.path_rel_to_cwd(agent_folder) + '/Dockerfile', empty_docker_template)

    return E.Success()


def register_agent_template(
        k_ctl: k.KubeCtl,
        file: fs.FileSystem,
        agent_name: str,
        agent_template_path: str,
        image_url: str,
        username: str,
        password: str,
        cluster_name: str):

    pod_template_text = file.read(file.path_rel_to_cwd(agent_template_path))

    payload = {
        'id': agent_name,
        'plugin_id': 'cd.go.contrib.elasticagent.kubernetes',
        'properties': [
            {'key': 'Image', 'value': image_url},
            {'key': 'PodConfiguration', 'value': pod_template_text},
            {'key': 'SpecifiedUsingPodConfiguration', 'value': 'true'},
            {'key': 'Privileged', 'value': 'true'}
        ]
    }

    return request(k_ctl, 'POST', '/go/api/elastic/profiles',
                   {'Accept': 'application/vnd.go.cd.v1+json'},
                   payload,
                   username, password, cluster_name)


def generate_agent_pod_template(agent_name: str, agent_image: str):
    template = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": agent_name+"-{{ POD_POSTFIX }}",
            "labels": {"app": agent_name}
        },
        "spec": {
            "serviceAccountName": "default",
            "volumes": [
                {"name": "ssh-secrets", "secret": {"secretName": "gocd-git-ssh"}}
            ],
            "containers": [
                {"name": agent_name+"-{{ CONTAINER_POSTFIX }}",
                 "image": agent_image,
                 "volumeMounts": [
                     {"name": "ssh-secrets",
                      "readOnly": True,
                      "mountPath": "/home/go/.ssh"}
                 ],
                 "securityContext": {"privileged": True}
                 }
            ]
        }
    }
    return template
