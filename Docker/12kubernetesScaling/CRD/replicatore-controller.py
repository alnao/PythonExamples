# replicatore-controller.py
import kopf
import kubernetes.client as k8s

@kopf.on.create('example.alnao.it', 'v1', 'replicatori')
@kopf.on.update('example.alnao.it', 'v1', 'replicatori')
def create_or_update(spec, name, namespace, logger, **kwargs):
    image = spec['image']
    replicas = spec['replicas']
    labels = {"app": name}

    apps_api = k8s.AppsV1Api()
    core_api = k8s.CoreV1Api()

    # Crea/aggiorna il Deployment
    deployment = k8s.V1Deployment(
        metadata=k8s.V1ObjectMeta(name=f"{name}-deployment"),
        spec=k8s.V1DeploymentSpec(
            replicas=replicas,
            selector=k8s.V1LabelSelector(match_labels=labels),
            template=k8s.V1PodTemplateSpec(
                metadata=k8s.V1ObjectMeta(labels=labels),
                spec=k8s.V1PodSpec(
                    containers=[
                        k8s.V1Container(
                            name="replicatore",
                            image=image,
                            ports=[k8s.V1ContainerPort(container_port=80)]
                        )
                    ]
                )
            )
        )
    )

    try:
        apps_api.read_namespaced_deployment(f"{name}-deployment", namespace)
        logger.info("🔁 Aggiorno deployment")
        apps_api.replace_namespaced_deployment(f"{name}-deployment", namespace, deployment)
    except k8s.exceptions.ApiException as e:
        if e.status == 404:
            logger.info("🚀 Creo deployment")
            apps_api.create_namespaced_deployment(namespace, deployment)
        else:
            raise

    # Crea/aggiorna il Service
    service = k8s.V1Service(
        metadata=k8s.V1ObjectMeta(name=f"{name}-service"),
        spec=k8s.V1ServiceSpec(
            selector=labels,
            ports=[k8s.V1ServicePort(port=80, target_port=80)]
        )
    )

    try:
        core_api.read_namespaced_service(f"{name}-service", namespace)
        logger.info("🔁 Aggiorno service")
        core_api.replace_namespaced_service(f"{name}-service", namespace, service)
    except k8s.exceptions.ApiException as e:
        if e.status == 404:
            logger.info("🚀 Creo service")
            core_api.create_namespaced_service(namespace, service)
        else:
            raise
