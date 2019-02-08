#!/usr/bin/env bash
set -e

CACHE_DIR=$1
CLUSTER_KUBECONFIG=$2
VAULT_ADDR=$3
VAULT_TOKEN=$4
VAULT_CA_B64=$5

cat > vaultingkube_ns.yaml <<-END
apiVersion: v1
kind: Namespace
metadata:
  name: vaultingkube
END
echo "Applying..."
echo "$(cat vaultingkube_ns.yaml)"
${CACHE_DIR}/kubectl apply -f vaultingkube_ns.yaml --kubeconfig ${CLUSTER_KUBECONFIG}
rm ./vaultingkube_ns.yaml || true

echo "Saving Vault CA as file..."
VAULT_CA_PATH="${CACHE_DIR}/vault_ca.pem"
echo "${VAULT_CA_B64}" | base64 --decode > ${VAULT_CA_PATH}

echo "Store vault CA..."
${CACHE_DIR}/kubectl create secret generic vaultca --namespace=vaultingkube --from-file=ca=${VAULT_CA_PATH}  --kubeconfig ${CLUSTER_KUBECONFIG} || true
rm -f ${VAULT_CA_PATH}

echo "Store vault token..."
${CACHE_DIR}/kubectl create secret generic vaulttoken --namespace=vaultingkube --from-literal=token=${VAULT_TOKEN}  --kubeconfig ${CLUSTER_KUBECONFIG} || true

cat > vaultingkube.yaml <<-END
apiVersion: v1
kind: ServiceAccount
metadata:
  name: vaultingkube
  namespace: vaultingkube
---
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
---
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
---
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
          value: ${VAULT_ADDR}
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
      securityContext: {}
      terminationGracePeriodSeconds: 30
---
END
echo "Applying..."
echo "$(cat vaultingkube.yaml)"
${CACHE_DIR}/kubectl apply -f vaultingkube.yaml --kubeconfig ${CLUSTER_KUBECONFIG}
rm ./vaultingkube.yaml || true


