from typing import List, Optional
from krogon.steps.step import Step
import krogon.kubemci.kubemci as km
import krogon.either as E


def global_load_balancer(name: str, clusters=List[str], using_https: Optional[bool] = False):
    return GclbStep(name, clusters, using_https)


class GclbStep(Step):
    def __init__(self, gclb_name: str, clusters: List[str], using_https: bool):
        super().__init__(name='global_load_balancer: ['+gclb_name+']')
        self.service_port = 80 if not using_https else 443
        self.gclb_name = gclb_name
        self.clusters = clusters

    def exec(self, k_mci: km.KubeMci) -> E.Either:
        return km.configure_gclb(k_mci, self.clusters, self.gclb_name, self.service_port)
