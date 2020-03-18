from typing import List, Any

import krogon.either as E


class K8sProvider:
    def get_clusters(self, by_regex: str) -> E.Either[List[str], Any]: pass
    def kubectl(self, command: str, cluster_name: str) -> E.Either[None, Any]: pass
