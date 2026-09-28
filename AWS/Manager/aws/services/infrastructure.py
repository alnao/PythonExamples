"""EFS, Auto Scaling Group, Load Balancer ed ECR."""

from aws.services import paginate


class AwsEfs:
    def __init__(self, session):
        self.client = session.client('efs')

    def file_systems(self):
        return paginate(self.client, 'describe_file_systems', 'FileSystems')

    def mount_targets(self, file_system_id):
        return self.client.describe_mount_targets(FileSystemId=file_system_id).get('MountTargets', [])


class AwsAutoScaling:
    def __init__(self, session):
        self.client = session.client('autoscaling')

    def groups(self):
        return paginate(self.client, 'describe_auto_scaling_groups', 'AutoScalingGroups')


class AwsLoadBalancers:
    def __init__(self, session):
        self.client = session.client('elbv2')

    def load_balancers(self):
        return paginate(self.client, 'describe_load_balancers', 'LoadBalancers')

    def target_groups(self, load_balancer_arn):
        """Target group del load balancer, ognuno con lo stato di salute dei suoi target."""
        groups = paginate(self.client, 'describe_target_groups', 'TargetGroups',
                          LoadBalancerArn=load_balancer_arn)
        for g in groups:
            g['Targets'] = self.client.describe_target_health(
                TargetGroupArn=g['TargetGroupArn']).get('TargetHealthDescriptions', [])
        return groups

    def listeners(self, load_balancer_arn):
        return paginate(self.client, 'describe_listeners', 'Listeners', LoadBalancerArn=load_balancer_arn)


class AwsEcr:
    def __init__(self, session):
        self.client = session.client('ecr')

    def repositories(self):
        return paginate(self.client, 'describe_repositories', 'repositories')

    def images(self, repository_name):
        images = paginate(self.client, 'describe_images', 'imageDetails', repositoryName=repository_name)
        return sorted(images, key=lambda i: str(i.get('imagePushedAt') or ''), reverse=True)
