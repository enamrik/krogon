from typing import Any
import krogon.either as E
import krogon.k8s.kubectl as k


class IstioHttpsConfig: pass


class HttpsCertConfig(IstioHttpsConfig):
    def __init__(self, server_certificate_path: str, private_key_path: str):
        self.server_certificate_path = server_certificate_path
        self.private_key_path = private_key_path


class LetsEncryptConfig(IstioHttpsConfig):
    def __init__(self, email: str, dns_host: str):
        self.email = email
        self.dns_host = dns_host


class HttpsResult:
    def __init__(self, using_https: bool):
        self.using_https = using_https

    @staticmethod
    def none():
        return HttpsResult(using_https=False)


def configure_https(istio_https: IstioHttpsConfig,
                    k_ctl: k.KubeCtl,
                    cluster_name: str) -> E.Either[HttpsResult, Any]:

    if isinstance(istio_https, HttpsCertConfig):
        return E.Success(HttpsResult(using_https=True))

    if isinstance(istio_https, LetsEncryptConfig):
        return E.Success(HttpsResult(using_https=True))






