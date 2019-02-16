import krogon.gcp.k8s.kubectl as k
import krogon.either as E
from .gocd_api import request
import json


def encrypt_secret(k_ctl: k.KubeCtl, plain_text: str, username: str, password: str, cluster_name: str):
    return request(k_ctl, 'POST', '/go/api/admin/encrypt',
                   {'Accept': 'application/vnd.go.cd.v1+json'},
                   {'value': plain_text},
                   username, password, cluster_name) \
            | E.then | (lambda r: json.loads(r)['encrypted_value'])
