from krogon.config import Config
from krogon.logger import Logger
from krogon.os import OS
import krogon.file_system as fs
import krogon.either as E


class Helm:
    def __init__(self,
                 config: Config,
                 os: OS,
                 log: Logger,
                 file: fs.FileSystem):

        self.config = config
        self.run = lambda cmd: os.run(cmd, log)
        self.is_macos = os.is_macos
        self.log = log
        self.file = file


def install_helm(helm: Helm):
    if helm.file.exists("{cache_dir}/helm".format(cache_dir=helm.config.cache_dir)):
        return E.Success()

    helm.log.info("INSTALLING DEPENDENCY: Installing helm...")
    cur_os = 'darwin' if helm.is_macos() else 'linux'
    return helm.run("cd {cache_dir} && mkdir helm && cd ./helm "
                    "&& curl -L https://storage.googleapis.com/kubernetes-helm/"
                    "helm-v2.12.1-{os}-amd64.tar.gz | tar zx && cp -rf ./{os}-amd64/* . "
                    "&& rm -r ./{os}-amd64"
                    .format(cache_dir=helm.config.cache_dir, os=cur_os))
