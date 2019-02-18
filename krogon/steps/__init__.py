import krogon.steps.deploy_in_clusters as k
import krogon.steps.deploy_in_clusters.k8s_step as k8s_step
import krogon.steps.gclb.gclb_step as gclb_step
import krogon.steps.deploy.deployment_manager_step as deployment_manager_step


deploy_in_clusters_step = k.k8s_micro_service_deployment.create_micro_service

deploy_in_clusters = k8s_step.deploy_in_clusters
global_load_balancer = gclb_step.global_load_balancer
deploy = deployment_manager_step.deploy

