import boto3
from botocore.exceptions import ClientError
from typing import List, Dict, Optional
import logging
#import os

class AwsAutoScaling:
    def __init__(self, profile_name, region_name: str = 'eu-west-1'):
        self.profile_name=profile_name
        boto3.setup_default_session(profile_name=self.profile_name)
        self.asg_client = boto3.client('autoscaling', region_name=region_name)
        self.ec2_client = boto3.client('ec2', region_name=region_name)
        self.logger = logging.getLogger(__name__)

    def describe_asg(self, asg_name: str) -> Optional[Dict]: #Ottiene i dettagli di un Auto Scaling Group specifico.
        try:
            response = self.asg_client.describe_auto_scaling_groups(
                AutoScalingGroupNames=[asg_name]
            )
            if response['AutoScalingGroups']:
                return response['AutoScalingGroups'][0]
            return None
        except ClientError as e:
            self.logger.error(f"Errore nel recupero dell'ASG {asg_name}: {str(e)}")
            raise

    def list_asgs(self) -> List[Dict]:
        try:
            paginator = self.asg_client.get_paginator('describe_auto_scaling_groups')
            asgs = []
            for page in paginator.paginate():
                asgs.extend(page['AutoScalingGroups'])
            return asgs
        except ClientError as e:
            self.logger.error(f"Errore nel listare gli ASG: {str(e)}")
            raise

    def update_capacity(self, asg_name: str, min_size: int = None, max_size: int = None, desired_capacity: int = None) -> bool:
        #Aggiorna la capacità di un Auto Scaling Group.
        try:
            update_args = {'AutoScalingGroupName': asg_name}
            if min_size is not None:
                update_args['MinSize'] = min_size
            if max_size is not None:
                update_args['MaxSize'] = max_size
            if desired_capacity is not None:
                update_args['DesiredCapacity'] = desired_capacity

            self.asg_client.update_auto_scaling_group(**update_args)
            return True
        except ClientError as e:
            self.logger.error(f"Errore nell'aggiornamento dell'ASG {asg_name}: {str(e)}")
            raise

    def set_instance_protection(self, asg_name: str, instance_ids: List[str], protected_from_scale_in: bool) -> bool:
        try:
            self.asg_client.set_instance_protection(
                AutoScalingGroupName=asg_name,
                InstanceIds=instance_ids,
                ProtectedFromScaleIn=protected_from_scale_in
            )
            return True
        except ClientError as e:
            self.logger.error(f"Errore nell'impostare la protezione per le istanze in {asg_name}: {str(e)}")
            raise


    def get_instance_health(self, asg_name: str) -> List[Dict]: #Ottiene lo stato di salute delle istanze in un ASG.
        try:
            response = self.asg_client.describe_auto_scaling_instances()
            return [
                instance for instance in response['AutoScalingInstances']
                if instance['AutoScalingGroupName'] == asg_name
            ]
        except ClientError as e:
            self.logger.error(f"Errore nel recupero dello stato delle istanze per {asg_name}: {str(e)}")
            raise

def main(profile):
    print("Aws Py Console - Aws Api Gateway START")
    o=AwsAutoScaling(profile)
    l=o.list_asgs()
    print(l)
    print("-----")
    if len(l)>0:
        s=o.get_instance_health( l[0]['AutoScalingGroupName'] ) 
        print(s)
        print("-----")
        d=o.describe_asg(l[0]['AutoScalingGroupName'])
        print(d)
        print("-----")
        t=o.update_capacity(l[0]['AutoScalingGroupName'],1,4,1)
        print(t)
        print("-----")
        d=o.describe_asg(l[0]['AutoScalingGroupName'])
        print(d)
        print("-----")
    
if __name__ == '__main__':
    main("default")