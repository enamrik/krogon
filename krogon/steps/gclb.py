from typing import List
from krogon.steps.step import Step
import krogon.scripts.scripter as scp
import krogon.either as E


def global_load_balancer(name: str, clusters=List[str]):
    return GclbStep(name, clusters)


class GclbStep(Step):
    def __init__(self, gclb_name: str, clusters=List[str]):
        super().__init__(name='global_load_balancer: ['+gclb_name+']')
        self.gclb_name = gclb_name
        self.clusters = clusters

    def exec(self, scripter: scp.Scripter) -> E.Either:
        return scp.configure_gclb(scripter, self.clusters, self.gclb_name)
