from krogon.encoding import to_base64
import krogon.either as E
import krogon.k8s.kubectl as k


class Vault:
    def __init__(self, k_ctl: k.KubeCtl):
        self.k_ctl = k_ctl


def configure_vault(vault: Vault,
                    cluster_name: str,
                    vault_address: str,
                    vault_token: str,
                    vault_ca_b64: str):

    return k.apply(vault.k_ctl,
                   [_vaultingkube_namespace_template()],
                   cluster_tag=cluster_name) \
           | E.then | (lambda _: k.apply(vault.k_ctl,
                                         _vaultingkube_templates(vault_address, vault_token, vault_ca_b64),
                                         cluster_tag=cluster_name))


def _vaultingkube_namespace_template():
    return """
apiVersion: v1
kind: Namespace
metadata:
  name: vaultingkube
    """


def _vaultingkube_templates(vault_address: str, vault_token: str, vault_ca_b64: str):

    return [
        """
apiVersion: v1
kind: Secret
metadata:
  name: vaultca
  namespace: vaultingkube
type: Opaque
data:
  ca: {vault_ca}
        """.format(vault_ca=vault_ca_b64),
        """
apiVersion: v1
kind: Secret
metadata:
  name: vaulttoken
  namespace: vaultingkube
type: Opaque
data:
  token: {vault_token}
        """.format(vault_token=to_base64(vault_token)),
        """
apiVersion: v1
kind: ServiceAccount
metadata:
  name: vaultingkube
  namespace: vaultingkube
        """,
        """
apiVersion: rbac.authorization.k8s.io/v1beta1
kind: ClusterRoleBinding
metadata:
  name: vaultingkube
  namespace: vaultingkube
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: vaultingkube
subjects:
- kind: ServiceAccount
  name: vaultingkube
  namespace: vaultingkube
        """,
        """
apiVersion: rbac.authorization.k8s.io/v1beta1
kind: ClusterRole
metadata:
  name: vaultingkube
  namespace: vaultingkube
rules:
- apiGroups:
  - ""
  resources:
  - configmaps
  - secrets
  verbs:
  - create
  - delete
  - get
  - list
  - patch
  - update
        """,
        """
apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  labels:
    app: vaultingkube
  name: vaultingkube
  namespace: vaultingkube
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vaultingkube
  strategy:
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
    type: RollingUpdate
  template:
    metadata:
      labels:
        app: vaultingkube
    spec:
      volumes:
       - name: secret-volume
         secret:
           secretName: vaultca
      containers:
      - volumeMounts:
          - name: secret-volume
            readOnly: true
            mountPath: "/etc/secret-volume"
        env:
        - name: VAULT_ADDR
          value: {vault_address}
        - name: VAULT_TOKEN
          valueFrom:
            secretKeyRef:
              name: vaulttoken
              key: token
        - name: VAULT_CAPATH
          value: "/etc/secret-volume/ca"
        - name: VK_DELETE_OLD
          value: "true"
        - name: VK_SYNC_PERIOD
          value: "30"
        - name: VK_VAULT_ROOT_MOUNT_PATH
          value: services
        image: sunshinekitty/vaultingkube:v0.2.0
        imagePullPolicy: Always
        name: vaultingkube
        resources:
          limits:
            cpu: 100m
            memory: 64Mi
          requests:
            cpu: 100m
            memory: 64Mi
        terminationMessagePath: /dev/termination-log
        terminationMessagePolicy: File
      dnsPolicy: ClusterFirst
      serviceAccountName: vaultingkube
      restartPolicy: Always
      schedulerName: default-scheduler
      securityContext: {{}}
      terminationGracePeriodSeconds: 30
       """.format(vault_address=vault_address)
    ]

