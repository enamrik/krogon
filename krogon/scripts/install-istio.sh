#!/usr/bin/env bash

set -e

CACHE_DIR=$1
ISTIO_VERSION=$2
KUBECONFIG=$3
GATEWAY_TYPE=$4

ISTIO_OPTIONS=" --set global.proxy.image=proxyv2 "
ISTIO_OPTIONS=$ISTIO_OPTIONS" --set global.mtls.enabled=false"
ISTIO_OPTIONS=$ISTIO_OPTIONS" --set sidecar-injector.enabled=true"
ISTIO_OPTIONS=$ISTIO_OPTIONS" --set prometheus.enabled=true"
ISTIO_OPTIONS=$ISTIO_OPTIONS" --set grafana.enabled=true"
ISTIO_OPTIONS=$ISTIO_OPTIONS" --set kiali.enabled=true"
ISTIO_OPTIONS=$ISTIO_OPTIONS" --set tracing.enabled=true "
ISTIO_OPTIONS=$ISTIO_OPTIONS" --set servicegraph.enabled=true"

echo "Installing istio from: $CACHE_DIR/istio-$ISTIO_VERSION ..."

${CACHE_DIR}/kubectl create namespace istio-system --kubeconfig ${KUBECONFIG}  || true
${CACHE_DIR}/helm/helm template ${CACHE_DIR}/istio-${ISTIO_VERSION}/install/kubernetes/helm/istio \
    --name istio \
    --namespace istio-system \
    ${ISTIO_OPTIONS} \
    --set gateways.istio-ingressgateway.type=${GATEWAY_TYPE} \
    --set "kiali.dashboard.jaegerURL=http://$(${CACHE_DIR}/kubectl get svc tracing --namespace istio-system -o jsonpath='{.spec.clusterIP}' --kubeconfig ${KUBECONFIG}):80" \
    --set "kiali.dashboard.grafanaURL=http://$(${CACHE_DIR}/kubectl get svc grafana --namespace istio-system -o jsonpath='{.spec.clusterIP}' --kubeconfig ${KUBECONFIG}):3000" \
    > ${CACHE_DIR}/istio.yaml
${CACHE_DIR}/kubectl apply -f ${CACHE_DIR}/istio.yaml --kubeconfig ${KUBECONFIG}
${CACHE_DIR}/kubectl label namespace default istio-injection=enabled --kubeconfig ${KUBECONFIG} || true

