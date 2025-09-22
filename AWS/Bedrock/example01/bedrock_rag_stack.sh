#!/bin/bash

# Example usage:
# ./bedrock_rag_stack.sh create ragdemo eu-central-1
# ./bedrock_rag_stack.sh destroy ragdemo eu-central-1

ACTION=${1:-create}                # create | destroy
PROJECT_NAME=${2:-ragdemo}          # es: ragdemo
REGION=${3:-eu-central-1} # default Frankfurt

# Parameters
BUCKET_NAME="$PROJECT_NAME-bucket"
ROLE_NAME="$PROJECT_NAME-role"
POLICY_NAME="$PROJECT_NAME-policy"
SG_NAME="$PROJECT_NAME-security-group"
EC2_NAME="$PROJECT_NAME-ec2"
KEY_NAME="alberto-nao-francoforte"  # Change with your EC2 Key Pair name
INSTANCE_TYPE="t3.micro"  # Free tier eligible

# Helper for AWS Profile (optional)
AWS_PROFILE=""

# Paths for temp files
POLICY_FILE=./policy.json #POLICY_FILE="/tmp/${POLICY_NAME}.json"
USER_DATA_FILE=./user_data.sh
INSTANCE_ID_FILE="/tmp/ec2_${PROJECT_NAME}.id"
SG_ID_FILE="/tmp/sg_${PROJECT_NAME}.id"
ROLE_ARN_FILE="/tmp/role_${PROJECT_NAME}.arn"

function create_stack() {
    echo "Creating Bedrock/RAG stack in $REGION..."

    # 1. Create S3 bucket
    echo "Creating S3 bucket: $BUCKET_NAME"
    aws $AWS_PROFILE s3api create-bucket --bucket $BUCKET_NAME --region $REGION --create-bucket-configuration LocationConstraint=$REGION

    # 2. Create IAM Policy
    echo "Creating IAM Policy: $POLICY_NAME"
    #    cat > $POLICY_FILE <<EOF
    #EOF
    aws $AWS_PROFILE iam create-policy --policy-name $POLICY_NAME --policy-document file://$POLICY_FILE

    # 3. Create IAM Role for EC2
    echo "Creating IAM Role: $ROLE_NAME"
    cat > /tmp/trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Service": "ec2.amazonaws.com" },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
    aws $AWS_PROFILE iam create-role --role-name $ROLE_NAME --assume-role-policy-document file:///tmp/trust-policy.json
    aws $AWS_PROFILE iam attach-role-policy --role-name $ROLE_NAME --policy-arn arn:aws:iam::$(aws $AWS_PROFILE sts get-caller-identity --query Account --output text):policy/$POLICY_NAME
    ROLE_ARN=$(aws $AWS_PROFILE iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text)
    echo $ROLE_ARN > $ROLE_ARN_FILE

    # 4. Create Security Group
    echo "Creating Security Group: $SG_NAME"
    VPC_ID=$(aws $AWS_PROFILE ec2 describe-vpcs --region $REGION --query 'Vpcs[0].VpcId' --output text)
    SG_ID=$(aws $AWS_PROFILE ec2 create-security-group --group-name $SG_NAME --description "Bedrock RAG SG" --vpc-id $VPC_ID --region $REGION --query 'GroupId' --output text)
    echo $SG_ID > $SG_ID_FILE

    # Open ports 22 (SSH), 8000 (FastAPI)
    aws $AWS_PROFILE ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 22 --cidr 0.0.0.0/0 --region $REGION
    aws $AWS_PROFILE ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 8000 --cidr 0.0.0.0/0 --region $REGION

    # 5. Launch EC2 instance
    echo "Launching EC2 instance: $EC2_NAME"
    AMI_ID=$(aws $AWS_PROFILE ec2 describe-images --region $REGION --owners amazon --filters "Name=name,Values=amzn2-ami-hvm-*-x86_64-gp2" --query 'Images[0].ImageId' --output text)
    INSTANCE_ID=$(aws $AWS_PROFILE ec2 run-instances --image-id $AMI_ID --count 1 \
        --instance-type $INSTANCE_TYPE --key-name $KEY_NAME \
        --security-group-ids $SG_ID --iam-instance-profile Name=$ROLE_NAME --region $REGION \
        --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$EC2_NAME}]" \
        --user-data file://$USER_DATA_FILE \
        --query 'Instances[0].InstanceId' --output text)
    echo $INSTANCE_ID > $INSTANCE_ID_FILE

    echo "Stack created!"
    echo "S3 bucket: $BUCKET_NAME"
    echo "IAM Role: $ROLE_NAME (attached policy: $POLICY_NAME)"
    echo "Security Group: $SG_NAME ($SG_ID)"
    echo "EC2 Instance: $EC2_NAME ($INSTANCE_ID)"
    echo "Delete temp files manually if non usati."
}

function destroy_stack() {
    echo "Destroying Bedrock/RAG stack in $REGION..."

    # 1. Terminate EC2
    INSTANCE_ID=$(cat $INSTANCE_ID_FILE 2>/dev/null)
    if [ ! -z "$INSTANCE_ID" ]; then
        echo "Terminating EC2 Instance $INSTANCE_ID"
        aws $AWS_PROFILE ec2 terminate-instances --instance-ids $INSTANCE_ID --region $REGION
    fi

    # 2. Delete Security Group
    SG_ID=$(cat $SG_ID_FILE 2>/dev/null)
    if [ ! -z "$SG_ID" ]; then
        echo "Deleting Security Group $SG_ID"
        aws $AWS_PROFILE ec2 delete-security-group --group-id $SG_ID --region $REGION
    fi

    # 3. Delete S3 bucket and its contents
    echo "Deleting S3 bucket: $BUCKET_NAME"
    aws $AWS_PROFILE s3 rm s3://$BUCKET_NAME --recursive
    aws $AWS_PROFILE s3api delete-bucket --bucket $BUCKET_NAME --region $REGION

    # 4. Detach and delete IAM policy, role
    echo "Detaching and deleting IAM policy/role"
    aws $AWS_PROFILE iam detach-role-policy --role-name $ROLE_NAME --policy-arn arn:aws:iam::$(aws $AWS_PROFILE sts get-caller-identity --query Account --output text):policy/$POLICY_NAME
    aws $AWS_PROFILE iam delete-policy --policy-arn arn:aws:iam::$(aws $AWS_PROFILE sts get-caller-identity --query Account --output text):policy/$POLICY_NAME
    aws $AWS_PROFILE iam delete-role --role-name $ROLE_NAME

    # 5. Delete temp files
    rm -f $POLICY_FILE $INSTANCE_ID_FILE $SG_ID_FILE $ROLE_ARN_FILE /tmp/trust-policy.json

    echo "Stack destroyed!"
}

if [[ "$ACTION" == "create" ]]; then
    create_stack
elif [[ "$ACTION" == "destroy" ]]; then
    destroy_stack
else
    echo "Usage: $0 create|destroy PROJECT_NAME [REGION]"
    exit 1
fi