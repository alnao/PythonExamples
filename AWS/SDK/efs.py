import boto3

class AwsEfs:
    def __init__(self, profile_name):
        self.profile_name=profile_name
        self.client = boto3.client('efs')
        boto3.setup_default_session(profile_name=self.profile_name)

    def create_file_system(self, creation_token):
        response = self.client.create_file_system(CreationToken=creation_token)
        if 'FileSystems' in response:
            return response['FileSystems']
        return response
    
    def describe_file_systems(self):
        response = self.client.describe_file_systems()
        if 'FileSystems' in response:
            return response['FileSystems']
        return []

    def create_mount_target(self, file_system_id, subnet_id):
        response = self.client.create_mount_target(
            FileSystemId=file_system_id,
            SubnetId=subnet_id
        )
        return response

    def delete_file_system(self, file_system_id):
        response = self.client.delete_file_system(FileSystemId=file_system_id)
        return response

    def describe_mount_targets(self, file_system_id):
        response = self.client.describe_mount_targets(FileSystemId=file_system_id)
        return response

    def tag_resource(self, resource_id, tags):
        response = self.client.tag_resource(
            ResourceId=resource_id,
            Tags=tags
        )
        return response

    def untag_resource(self, resource_id, tag_keys):
        response = self.client.untag_resource(
            ResourceId=resource_id,
            TagKeys=tag_keys
        )
        return response
def main(profile):
    print("Aws Py Console - Ec2 Instances START")
    efs=AwsEfs(profile)
    l=efs.describe_file_systems()

#[{'OwnerId': '740456629644', 'CreationToken': 'FileSystem-KoU3b20z36HO', 'FileSystemId': 'fs-0da9f1c0604153db5', 'FileSystemArn': 
# 'arn:aws:elasticfilesystem:eu-west-1:740456629644:file-system/fs-0da9f1c0604153db5',
#  'CreationTime': datetime.datetime(2024, 10, 21, 10, 56, 36, tzinfo=tzlocal()), 'LifeCycleState': 'available', 'Name': 
# 'Esempio18efs', 'NumberOfMountTargets': 1, 'SizeInBytes':
#  {'Value': 12288, 'Timestamp': datetime.datetime(2024, 10, 21, 11, 59, 22, tzinfo=tzlocal()), 'ValueInIA': 0, 'ValueInStandard': 12288, 
# 'ValueInArchive': 0}, 'PerformanceMode': 'generalPurpose', 'Encrypted': True, 'KmsKeyId':
#  'arn:aws:kms:eu-west-1:740456629644:key/7483a7d4-cded-4d6d-a9ba-134a5545503d', 'ThroughputMode': 'bursting', 'Tags': [{'Key': 'Name', 
# 'Value': 'Esempio18efs'}], 'FileSystemProtection': {'ReplicationOverwriteProtection': 'ENABLED'}},
# {'OwnerId': '740456629644', 'CreationToken': 'quickCreated-7db07439-4c55-424a-85ea-a5f54196b6fa', 'FileSystemId': 
# 'fs-0baed24c56c977151', 'FileSystemArn': 'arn:aws:elasticfilesystem:eu-west-1:740456629644:file-system/fs-0baed24c56c977151', 
# 'CreationTime': datetime.datetime(2023, 2, 16, 9, 8, 58, tzinfo=tzlocal()), 'LifeCycleState': 'available', 'Name': 'testAlbertoEFS', 
# 'NumberOfMountTargets': 2, 'SizeInBytes': {'Value': 73728, 'Timestamp': datetime.datetime(2024, 10, 21, 11, 59, 25, tzinfo=tzlocal()),
#  'ValueInIA': 0, 'ValueInStandard': 73728, 'ValueInArchive': 0}, 'PerformanceMode': 'generalPurpose', 'Encrypted': True, 
# 'KmsKeyId': 'arn:aws:kms:eu-west-1:740456629644:key/7483a7d4-cded-4d6d-a9ba-134a5545503d', 'ThroughputMode': 'bursting', 
# 'Tags': [{'Key': 'Name', 'Value': 'testAlbertoEFS'}, {'Key': 'aws:elasticfilesystem:default-backup', 'Value': 'enabled'}], 
# 'FileSystemProtection': {'ReplicationOverwriteProtection': 'ENABLED'}}]        
    print(l)
    if len(l)>0:
        d=efs.describe_mount_targets(l[0]['FileSystemId'])
        print(d)


if __name__ == '__main__':
    main("default")