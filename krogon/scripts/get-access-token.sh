#!/usr/bin/env bash
set -e

CACHE_DIR=$1
CLUSTER_KUBECONFIG=$2

echo "GET-ACCESS-TOKEN:  ARGS: cache: ${CACHE_DIR}, kconfig: ${CLUSTER_KUBECONFIG}"

cat > ${CACHE_DIR}/get_access_token.yaml <<-END
apiVersion: v1
kind: ServiceAccount
metadata:
  name: deploy-admin
  namespace: kube-system
---
apiVersion: rbac.authorization.k8s.io/v1beta1
kind: ClusterRoleBinding
metadata:
  name: deploy-admin
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
  - kind: ServiceAccount
    name: deploy-admin
    namespace: kube-system
END

echo "GET-ACCESS-TOKEN:  Applying..."
${CACHE_DIR}/kubectl apply -f ${CACHE_DIR}/get_access_token.yaml --kubeconfig ${CLUSTER_KUBECONFIG}
rm ${CACHE_DIR}/get_access_token.yaml || true

echo "GET-ACCESS-TOKEN:  ${CACHE_DIR}/kubectl -n kube-system get secret --kubeconfig ${CLUSTER_KUBECONFIG} | grep deploy-admin | awk '{print $1}'"
SECRET=$(${CACHE_DIR}/kubectl -n kube-system get secret --kubeconfig ${CLUSTER_KUBECONFIG} | grep deploy-admin | awk '{print $1}')

echo "GET-ACCESS-TOKEN:  ${CACHE_DIR}/kubectl -n kube-system describe secret ${SECRET} --kubeconfig ${CLUSTER_KUBECONFIG}"
OUTPUT=$(${CACHE_DIR}/kubectl -n kube-system describe secret ${SECRET} --kubeconfig ${CLUSTER_KUBECONFIG})
echo "GET-ACCESS-TOKEN:  ${OUTPUT}"

