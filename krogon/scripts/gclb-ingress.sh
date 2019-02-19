#!/usr/bin/env bash

set -e

ACTION=$1
CACHE_DIR=$2
KUBECONFIG=$3
GLOBAL_LB_NAME=$4
PROJECT=$5
SERVICE_PORT=$6
KEY_FILE=$7


echo "Activating account..."
export GOOGLE_APPLICATION_CREDENTIALS=${KEY_FILE}
export PATH=$PATH:${CACHE_DIR}
${CACHE_DIR}/google-cloud-sdk/bin/gcloud config set project ${PROJECT}
${CACHE_DIR}/google-cloud-sdk/bin/gcloud auth activate-service-account --key-file ${KEY_FILE} || exit 1

cat > ${CACHE_DIR}/temp.yaml <<-END
---
apiVersion: extensions/v1beta1
kind: Ingress
metadata:
  name: global-lb
  namespace: istio-system
  annotations:
    kubernetes.io/ingress.global-static-ip-name: ${GLOBAL_LB_NAME}
    kubernetes.io/ingress.class: gce-multi-cluster
spec:
  backend:
    nameSpace: istio-system
    serviceName: istio-ingressgateway
    servicePort: ${SERVICE_PORT}
END

echo "YAML: ${CACHE_DIR}/temp.yaml"

echo "COMMAND: ${CACHE_DIR}/kubemci ${ACTION} ${GLOBAL_LB_NAME} \
        --ingress=${CACHE_DIR}/temp.yaml \
        --gcp-project=${PROJECT} \
        --kubeconfig=${KUBECONFIG}"

${CACHE_DIR}/kubemci ${ACTION} ${GLOBAL_LB_NAME} \
        --ingress=${CACHE_DIR}/temp.yaml \
        --force \
        --gcp-project=${PROJECT} \
        --kubeconfig=${KUBECONFIG}

#rm ${CACHE_DIR}/temp.yaml || true

