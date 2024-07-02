import boto3
#see https://docs.aws.amazon.com/code-library/latest/ug/python_3_ec2_code_examples.html
#see https://github.com/awsdocs/aws-doc-sdk-examples/tree/main/python/example_code/ec2#code-examples

#see https://boto3.amazonaws.com/v1/documentation/api/latest/guide/ec2-example-managing-instances.html
#see #https://medium.com/featurepreneur/using-ec2-services-using-boto3-ad5453fe3bea

class AwsEc2:
    def __init__(self, profile_name):
        self.profile_name=profile_name

    def get_lista_istanze(self):
        boto3.setup_default_session(profile_name=self.profile_name)
        ec2 = boto3.client('ec2')
        response = ec2.describe_instances()
        return response

    def set_tag(self,instance_id, tag_key, tag_value):
        if tag_key=='':
            return
        ec2 = boto3.resource('ec2')# region_name=AWS_REGION)
        tags=[{'Key': tag_key,'Value': tag_value}]
        instances = ec2.instances.filter(InstanceIds=[instance_id,],)
        for instance in instances:
            instance.create_tags(Tags=tags)
        print("set_tag "  + instance_id)
        return tags

    #https://medium.com/featurepreneur/using-ec2-services-using-boto3-ad5453fe3bea
    def stop_instance(self,instance_id):
        ec2_client = boto3.client('ec2')#, region_name=”us-west-2"
        print ("stop_instance " + instance_id)
        response = ec2_client.stop_instances(InstanceIds=[instance_id])
        return response

    def start_instance(self,instance_id):
        ec2_client = boto3.client('ec2')
        print ("start_instance " + instance_id)
        response = ec2_client.start_instances(InstanceIds=[instance_id])
        return response

    #def terminate_instance(instance_id):
    # why define a terminate instance method ?



#see https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2/securitygroup/index.html
class AwsEc2SecurityGroup:
    def __init__(self, profile_name):
        self.profile_name=profile_name

    def get_list(self):
        boto3.setup_default_session(profile_name=self.profile_name)
        ec2_client = boto3.client('ec2')
        response = ec2_client.describe_security_groups()
        if 'SecurityGroups' in response:
            return response['SecurityGroups']
        return []
    def describe_security_group(self,sg_name):
        response=self.get_list()
        if len(response)>0:
            r=[]
            for e in response:
                if e["GroupName"]==sg_name:
                    r.append(e) 
            return r
        return []

    #see #https://docs.aws.amazon.com/it_it/AWSEC2/latest/UserGuide/example_ec2_CreateSecurityGroup_section.html
    def create(self,group_name, vpc =""):
        ec2_resource = boto3.resource("ec2")
        if vpc !="" :
            ret= ec2_resource.create_security_group(GroupName=group_name, Description=group_name, VpcId=vpc )
        else:
            ret= ec2_resource.create_security_group(GroupName=group_name, Description=group_name)
        return ret
    
    #see https://kiamatthews.medium.com/using-python-to-add-rules-to-an-aws-security-group-ee56def5bf78
    def add_permission(self,security_group_id,port_range_start,port_range_end,protocol,cidr,description=''): 
        ec2_resource = boto3.resource("ec2")
        security_group = ec2_resource.SecurityGroup(security_group_id)
        security_group.authorize_ingress(DryRun=False,
            IpPermissions=[
                {
                    'FromPort': port_range_start,
                    'ToPort': port_range_end,
                    'IpProtocol': protocol,
                    'IpRanges': [
                        {
                            'CidrIp': cidr,
                            'Description': description
                        },
                    ]
                }
            ]
        )
    def revoke_all_permission(self, security_group_id): #use this to remove all rules from the group
        ec2_resource = boto3.resource("ec2")
        security_group = ec2_resource.SecurityGroup(security_group_id)
        security_group.revoke_ingress(IpPermissions=security_group.ip_permissions)
        
def main(profile):
    print("Aws Py Console - Ec2 Instances START")
    ec2=AwsEc2(profile)
    lista= ec2.get_lista_istanze()
    print (lista)
    print("---")
    ec2sg=AwsEc2SecurityGroup(profile)
    lista= ec2sg.get_list()
    print (lista)
    #print("---")
    #sg_name="prova-sdk"
    #vpc="vpc-0013c2751d04a7413"
    #r = ec2sg.create(sg_name,vpc)
    #print(r) #ec2.SecurityGroup(id='sg-0936051132e4a5e5d')
    #sg_id="sg-0936051132e4a5e5d"
    #ec2sg.add_permission(sg_id,port_range_start=80,port_range_end=80,protocol="TCP",cidr="0.0.0.0/0",description='ottanta')
    #ec2sg.revoke_all_permission(sg_id) #use this to remove all rules from the group
    #r = ec2sg.describe_security_group(sg_name)
    #print(r)
    #def add_permission(self,security_group_id,port_range_start,port_range_end,protocol,cidr,description=''):
    #def revoke_all_permission(self, security_group_id): #use this to remove all rules from the group


if __name__ == '__main__':
    main("default")