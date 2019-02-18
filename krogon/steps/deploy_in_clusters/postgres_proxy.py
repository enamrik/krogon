import krogon.steps.deploy.postgres as p


class PostgresProxy:
    def __init__(self, project: str, service_name: str, db_name: str, db_region: str, service_account_b64: str):
        self.service_name = service_name
        self.project = project
        self.db_name = db_name
        self.db_region = db_region
        self.service_account_b64 = service_account_b64

    def container(self):
        instance_connection_name = p.instance_connection_name(self.project, self.db_name, self.db_region)
        return {
            'name': 'cloudsql-proxy',
            'image': 'gcr.io/cloudsql-docker/gce-proxy:1.11',
            'command': ["/cloud_sql_proxy",
                        "-instances=" + instance_connection_name + "=tcp:5432",
                        "-credential_file=/secrets/cloudsql/credentials"],
            'securityContext': {
                'runAsUser': 2,
                'allowPrivilegeEscalation': False,
            },
            'volumeMounts': [
                {'name': self._cloudsql_secret(self.service_name),
                 'mountPath': '/secrets/cloudsql',
                 'readOnly': True}
            ]
        }

    def credential_file_secret(self):
        return {
            'apiVersion': 'v1',
            'kind': 'Secret',
            'metadata': {'name': self._cloudsql_secret(self.service_name)},
            'type': 'Opaque',
            'data': {'credentials': self.service_account_b64}
        }

    def volume(self):
        return {
            'name': self._cloudsql_secret(self.service_name),
            'secret': {'secretName': self._cloudsql_secret(self.service_name)}
        }

    @staticmethod
    def _cloudsql_secret(service_name):
        return service_name + '-cloudsql-instance-cred'


