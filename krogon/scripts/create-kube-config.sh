#!/usr/bin/env bash

set -e

CLUSTER_NAME=$1
CACHE_DIR=$2
KEY_FILE=$3
CLUSTER_KUBECONFIG=$4
PROJECT=$5


echo "CREATE-KUBE-CONFIG:  ARGS: cluster: $CLUSTER_NAME, cache_dir: $CACHE_DIR, key_file: $KEY_FILE, project: ${PROJECT}"

export GOOGLE_APPLICATION_CREDENTIALS=${KEY_FILE}
export PATH=$PATH:${CACHE_DIR}
${CACHE_DIR}/google-cloud-sdk/bin/gcloud config set project ${PROJECT}
${CACHE_DIR}/google-cloud-sdk/bin/gcloud auth activate-service-account --key-file ${KEY_FILE} || exit 1

REGION=$(${CACHE_DIR}/google-cloud-sdk/bin/gcloud container clusters list --format="value(location)" --filter="NAME=${CLUSTER_NAME}")
echo "CREATE-KUBE-CONFIG:  Region: ${REGION}"

echo "CREATE-KUBE-CONFIG:  Get credentials: KUBECONFIG=${CLUSTER_KUBECONFIG} ${CACHE_DIR}/google-cloud-sdk/bin/gcloud \
    container clusters --region ${REGION} get-credentials ${CLUSTER_NAME}"

KUBECONFIG=${CLUSTER_KUBECONFIG} ${CACHE_DIR}/google-cloud-sdk/bin/gcloud \
    container clusters --region ${REGION} get-credentials ${CLUSTER_NAME}

USER=$(${CACHE_DIR}/google-cloud-sdk/bin/gcloud config get-value account || exit 1)

echo "CREATE-KUBE-CONFIG:  USER: ${USER}"

chmod u+x ${CACHE_DIR}/kubectl

EXISTING_USER=$(${CACHE_DIR}/kubectl get clusterrolebindings ${USER} --all-namespaces \
    --kubeconfig ${CLUSTER_KUBECONFIG} -o jsonpath='{.subjects[0].name}' || true)

echo "CREATE-KUBE-CONFIG:  User is: ${USER}, Binding found: ${EXISTING_USER}"

if [ -z $EXISTING_USER ]; then
    echo "CREATE-KUBE-CONFIG:  Creating binding...${CACHE_DIR}/kubectl create clusterrolebinding ${USER} \
        --clusterrole cluster-admin \
        --user ${USER} \
        --kubeconfig ${CLUSTER_KUBECONFIG}"

    ${CACHE_DIR}/kubectl create clusterrolebinding ${USER} \
        --clusterrole cluster-admin \
        --user ${USER} \
        --kubeconfig ${CLUSTER_KUBECONFIG}
else
    echo "CREATE-KUBE-CONFIG:  Binding already exists."
fi



