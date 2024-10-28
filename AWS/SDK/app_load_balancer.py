import boto3
from botocore.exceptions import ClientError
from typing import List, Dict, Optional, Union
import logging

class AwsAppLoadBalancer:
    def __init__(self, profile_name, region_name: str = 'eu-west-1'):
        self.profile_name=profile_name
        boto3.setup_default_session(profile_name=self.profile_name)
        self.elbv2_client = boto3.client('elbv2', region_name=region_name)
        self.logger = logging.getLogger(__name__)

    def describe_load_balancers(self, names: List[str] = None) -> List[Dict]: #Ottiene i dettagli di uno o più ALB.
        try:
            if names:
                response = self.elbv2_client.describe_load_balancers(Names=names)
            else:
                response = self.elbv2_client.describe_load_balancers()
            return response['LoadBalancers']
        except ClientError as e:
            self.logger.error(f"Errore nel recupero degli ALB: {str(e)}")
            raise

    def get_load_balancer_by_name(self, name: str) -> Optional[Dict]: # Ottiene i dettagli di un ALB specifico per nome.
        try:
            response = self.elbv2_client.describe_load_balancers(Names=[name])
            return response['LoadBalancers'][0] if response['LoadBalancers'] else None
        except ClientError as e:
            if e.response['Error']['Code'] == 'LoadBalancerNotFound':
                return None
            self.logger.error(f"Errore nel recupero dell'ALB {name}: {str(e)}")
            raise

    def describe_target_groups(self, load_balancer_arn: str = None) -> List[Dict]: #Ottiene i target groups associati a un ALB.
        try:
            if load_balancer_arn:
                response = self.elbv2_client.describe_target_groups(
                    LoadBalancerArn=load_balancer_arn
                )
            else:
                response = self.elbv2_client.describe_target_groups()
            return response['TargetGroups']
        except ClientError as e:
            self.logger.error(f"Errore nel recupero dei target groups: {str(e)}")
            raise

    def describe_target_health(self, target_group_arn: str) -> List[Dict]: #Ottiene lo stato di salute dei target in un target group.
        try:
            response = self.elbv2_client.describe_target_health(
                TargetGroupArn=target_group_arn
            )
            return response['TargetHealthDescriptions']
        except ClientError as e:
            self.logger.error(f"Errore nel recupero dello stato dei target: {str(e)}")
            raise

    def describe_listeners(self, load_balancer_arn: str) -> List[Dict]: #Ottiene i listener configurati su un ALB.
        try:
            response = self.elbv2_client.describe_listeners(
                LoadBalancerArn=load_balancer_arn
            )
            return response['Listeners']
        except ClientError as e:
            self.logger.error(f"Errore nel recupero dei listener: {str(e)}")
            raise


def main(profile):
    print("Aws Py Console - Aws App Load balancer START")
    o=AwsAppLoadBalancer(profile)
    l=o.describe_load_balancers()
    print(l)
    print("-----") #LoadBalancerName
    if len(l)>0:
        d=o.get_load_balancer_by_name(l[0]['LoadBalancerName'])
        print(d)
        print("-----") #LoadBalancerName
        t=o.describe_target_groups(l[0]['LoadBalancerArn'])
        print(t)
        print("-----") #LoadBalancerName
        s=o.describe_target_health(t[0]['TargetGroupArn'])
        print(s)
        print("-----") #LoadBalancerName
        s=o.describe_listeners(l[0]['LoadBalancerArn'])
        print(s)
        print("-----") #LoadBalancerName
    
if __name__ == '__main__':
    main("default")