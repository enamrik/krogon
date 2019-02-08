#!/usr/bin/env bash

set -e

ACTION=$1
CACHE_DIR=$2
KUBECONFIG=$3

cat > ${CACHE_DIR}/g_temp.yaml <<-END
---
apiVersion: v1
kind: Service
metadata:
  name: healthcheck-svc
spec:
  type: ClusterIP
  selector:
    app: healthcheck
  ports:
  - port: 80
    targetPort: 3000
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: healthcheck-dp
  labels:
    app: healthcheck
spec:
  replicas: 1
  selector:
    matchLabels:
      app: healthcheck
  template:
    metadata:
      labels:
        app: healthcheck
    spec:
      containers:
        - name: healthcheck
          image: gcr.io/prod-nbcuniversaltech/healthcheck:1.0.0
          ports:
            - containerPort: 3000
---
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: healthcheck-vs
spec:
  hosts:
    - "*"
  gateways:
    - cluster-gateway
  http:
    - route:
        - destination:
            host: healthcheck-svc

---
apiVersion: networking.istio.io/v1alpha3
kind: Gateway
metadata:
  name: cluster-gateway
spec:
  selector:
    # Which pods we want to expose as Istio router
    # This label points to the default one installed from file istio-demo.yaml
    istio: ingressgateway
  servers:
    - port:
        number: 80
        name: http
        protocol: HTTP
      # Here we specify which Kubernetes service names
      # we want to serve through this Gateway
      hosts:
        - "*"
END

if [ $ACTION == "uninstall" ]; then
    ${CACHE_DIR}/kubectl delete -f ${CACHE_DIR}/g_temp.yaml --kubeconfig ${KUBECONFIG} || true
fi

if [ $ACTION == "install" ]; then
    cat ${CACHE_DIR}/g_temp.yaml
    ${CACHE_DIR}/kubectl apply -f ${CACHE_DIR}/g_temp.yaml --kubeconfig ${KUBECONFIG}
fi

rm ${CACHE_DIR}/g_temp.yaml || true

