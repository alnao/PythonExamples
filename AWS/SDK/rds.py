import json
import boto3
#see https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ssm/client/get_parameters_by_path.html


class AwsRds:
    def __init__(self, profile_name):
        self.profile_name=profile_name
    def db_instances_list(self):
        boto3.setup_default_session(profile_name=self.profile_name)
        rds_client = boto3.client('rds')
        response = rds_client.describe_db_instances(
                    #DBInstanceIdentifier=instance_id
        )
        if "DBInstances" in response:
            return response["DBInstances"]
        return []

def main():
    print("Aws Py Console - RDS START")
    d=AwsRds("default")
    l=d.db_instances_list()
    print("-----------")
    for t in l:
        print(t['DBInstanceIdentifier'] + " " + t['Engine'])
    print("-----------")


if __name__ == '__main__':
    main()
