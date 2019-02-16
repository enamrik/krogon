from typing import Optional
import krogon.gcp.k8s.kubectl as k
import krogon.either as E
import json


def request(k_ctl: k.KubeCtl, method: str, path: str, headers: dict, body: Optional[dict],
            username: Optional[str], password: Optional[str], cluster_name: str):

    headers = list(map(
        lambda kv: "-H '{key}: {value}'".format(key=kv[0], value=kv[1]),
        headers.items())
    )
    headers = ' '.join(headers)

    body = "-d '{}'".format(json.dumps(body).replace("'", "\'")) \
        if body is not None \
        else ''

    credentials = "-u '{}:{}'".format(username, password) \
        if username is not None and password is not None \
        else ''

    cmd = ("curl -v 'http://localhost:8153{path}' " +
           "{credentials} " +
           "-H 'Content-Type: application/json' " +
           "{headers} " +
           "-X {method} {body}") \
        .format(method=method, headers=headers,
                credentials=credentials, path=path,
                body=body,
                username=username, password=password)

    return k.kubectl(k_ctl, cluster_name, command='get pods -l app=gocd,component=server  -o name') \
           | E.then | (lambda pod_name: k.kubectl(k_ctl,
                                                  cluster_name,
                                                  command='exec {} -- {}'.format(
                                                      pod_name.replace("pod/", ""),
                                                      cmd)))
