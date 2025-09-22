#!/bin/bash

# Example usage:
# ./bedrock_rag_stack.sh create ragdemo eu-central-1
# ./bedrock_rag_stack.sh destroy ragdemo eu-central-1

# Disabilita paginazione aws cli
set -e
export AWS_PAGER=""

ACTION=${1:-create}                # create | destroy
PROJECT_NAME=${2:-ragdemo}          # es: ragdemo
REGION=${3:-eu-central-1} # default Frankfurt

# Parameters
BUCKET_NAME="$PROJECT_NAME-alnao-bucket"
ROLE_NAME="$PROJECT_NAME-role"
POLICY_NAME="$PROJECT_NAME-policy"
SG_NAME="$PROJECT_NAME-security-group"
EC2_NAME="$PROJECT_NAME-ec2"
KEY_NAME="alberto-nao-francoforte"  # Change with your EC2 Key Pair name
INSTANCE_TYPE="t3.micro"  # Free tier eligible

VPC_ID=$(aws $AWS_PROFILE ec2 describe-vpcs --region $REGION --query 'Vpcs[0].VpcId' --output text)

# Helper for AWS Profile (optional)
AWS_PROFILE=""

# Paths for temp files
POLICY_FILE=./policy.json #POLICY_FILE="/tmp/${POLICY_NAME}.json"
USER_DATA_FILE=./user_data.sh
ROLE_ARN_FILE="/tmp/role_${PROJECT_NAME}.arn"

function create_stack() {
    echo "Creating Bedrock/RAG stack in $REGION..."

    # 1. Create S3 bucket if not exists
    if aws $AWS_PROFILE s3api head-bucket --bucket $BUCKET_NAME 2>/dev/null; then
        echo "S3 bucket $BUCKET_NAME already exists. Skipping creation."
    else
        echo "Creating S3 bucket: $BUCKET_NAME"
        aws $AWS_PROFILE s3api create-bucket --bucket $BUCKET_NAME --region $REGION --create-bucket-configuration LocationConstraint=$REGION
        aws $AWS_PROFILE s3api put-bucket-tagging --bucket $BUCKET_NAME --tagging "TagSet=[{Key=PROJECT_NAME,Value=$PROJECT_NAME}]"
    fi

    # 2. Create IAM Policy if not exists
    POLICY_ARN="arn:aws:iam::$(aws $AWS_PROFILE sts get-caller-identity --query Account --output text):policy/$POLICY_NAME"
    if aws $AWS_PROFILE iam get-policy --policy-arn $POLICY_ARN 2>/dev/null; then
        echo "IAM Policy $POLICY_NAME already exists. Skipping creation."
    else
        echo "Creating IAM Policy: $POLICY_NAME"
        aws $AWS_PROFILE iam create-policy --policy-name $POLICY_NAME --policy-document file://$POLICY_FILE --tags Key=PROJECT_NAME,Value=$PROJECT_NAME
    fi

    # 3. Create IAM Role for EC2 if not exists
    if aws $AWS_PROFILE iam get-role --role-name $ROLE_NAME 2>/dev/null; then
        echo "IAM Role $ROLE_NAME already exists. Skipping creation."
    else
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
        aws $AWS_PROFILE iam create-role --role-name $ROLE_NAME --assume-role-policy-document file:///tmp/trust-policy.json --tags Key=PROJECT_NAME,Value=$PROJECT_NAME
    fi
        aws $AWS_PROFILE iam attach-role-policy --role-name $ROLE_NAME --policy-arn $POLICY_ARN || true
        ROLE_ARN=$(aws $AWS_PROFILE iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text)
        echo $ROLE_ARN > $ROLE_ARN_FILE

    # 3.1. Create Instance Profile and add the role to it if not exists
    if aws $AWS_PROFILE iam get-instance-profile --instance-profile-name $ROLE_NAME 2>/dev/null; then
        echo "Instance Profile $ROLE_NAME already exists. Skipping creation."
    else
        echo "Creating Instance Profile: $ROLE_NAME"
        aws $AWS_PROFILE iam create-instance-profile --instance-profile-name $ROLE_NAME --tags Key=PROJECT_NAME,Value=$PROJECT_NAME
        sleep 5
    fi
    # Add role to instance profile if not already present
    if ! aws $AWS_PROFILE iam get-instance-profile --instance-profile-name $ROLE_NAME --query "InstanceProfile.Roles[?RoleName=='$ROLE_NAME']" --output text | grep $ROLE_NAME; then
        aws $AWS_PROFILE iam add-role-to-instance-profile --instance-profile-name $ROLE_NAME --role-name $ROLE_NAME
    fi
    # Wait a moment for the instance profile to be ready
    echo "Waiting for instance profile to be ready..."
    sleep 10

    # 4. Create Security Group if not exists
    SG_ID=$(aws $AWS_PROFILE ec2 describe-security-groups --region $REGION --filters Name=group-name,Values=$SG_NAME Name=vpc-id,Values=$VPC_ID --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null)
    if [ "$SG_ID" == "None" ] || [ -z "$SG_ID" ]; then
        echo "Creating Security Group: $SG_NAME"
        SG_ID=$(aws $AWS_PROFILE ec2 create-security-group --group-name $SG_NAME --description "Bedrock RAG SG" --vpc-id $VPC_ID --region $REGION --query 'GroupId' --output text)
        aws $AWS_PROFILE ec2 create-tags --resources $SG_ID --tags Key=PROJECT_NAME,Value=$PROJECT_NAME --region $REGION
    else
        echo "Security Group $SG_NAME already exists. Skipping creation."
        # Ensure SG_ID is set to the existing security group ID
        SG_ID=$(aws $AWS_PROFILE ec2 describe-security-groups --region $REGION --filters Name=group-name,Values=$SG_NAME Name=vpc-id,Values=$VPC_ID --query 'SecurityGroups[0].GroupId' --output text)
    fi
    

    # Open ports 22 (SSH), 8000 (FastAPI) only if not present
    # Port 22
    echo "Checking if port 22 rule exists..."
    RULE_22_EXISTS=$(aws $AWS_PROFILE ec2 describe-security-groups --group-ids $SG_ID --region $REGION --query "SecurityGroups[0].IpPermissions[?FromPort==\`22\` && IpProtocol=='tcp'].IpRanges[?CidrIp=='0.0.0.0/0']" --output text || echo "")
    if [ -n "$RULE_22_EXISTS" ]; then
        echo "Port 22 ingress rule already exists. Skipping."
    else
        echo "Adding port 22 ingress rule..."
        aws $AWS_PROFILE ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 22 --cidr 0.0.0.0/0 --region $REGION || echo "Failed to add port 22 rule (might already exist)"
    fi
    
    # Port 8000
    echo "Checking if port 8000 rule exists..."
    RULE_8000_EXISTS=$(aws $AWS_PROFILE ec2 describe-security-groups --group-ids $SG_ID --region $REGION --query "SecurityGroups[0].IpPermissions[?FromPort==\`8000\` && IpProtocol=='tcp'].IpRanges[?CidrIp=='0.0.0.0/0']" --output text || echo "")
    if [ -n "$RULE_8000_EXISTS" ]; then
        echo "Port 8000 ingress rule already exists. Skipping."
    else
        echo "Adding port 8000 ingress rule..."
        aws $AWS_PROFILE ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 8000 --cidr 0.0.0.0/0 --region $REGION || echo "Failed to add port 8000 rule (might already exist)"
    fi
    
    # Port 80 (HTTP)
    echo "Checking if port 80 rule exists..."
    RULE_80_EXISTS=$(aws $AWS_PROFILE ec2 describe-security-groups --group-ids $SG_ID --region $REGION --query "SecurityGroups[0].IpPermissions[?FromPort==\`80\` && IpProtocol=='tcp'].IpRanges[?CidrIp=='0.0.0.0/0']" --output text || echo "")
    if [ -n "$RULE_80_EXISTS" ]; then
        echo "Port 80 ingress rule already exists. Skipping."
    else
        echo "Adding port 80 ingress rule..."
        aws $AWS_PROFILE ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 80 --cidr 0.0.0.0/0 --region $REGION || echo "Failed to add port 80 rule (might already exist)"
    fi

    
    # 5. Launch EC2 instance
    echo "Launching EC2 instance: $EC2_NAME"
    AMI_ID=$(aws $AWS_PROFILE ec2 describe-images --region $REGION --owners amazon --filters "Name=name,Values=amzn2-ami-hvm-*-x86_64-gp2" --query 'Images[0].ImageId' --output text)
    INSTANCE_ID=$(aws $AWS_PROFILE ec2 run-instances --image-id $AMI_ID --count 1 \
        --instance-type $INSTANCE_TYPE --key-name $KEY_NAME \
        --security-group-ids $SG_ID --iam-instance-profile Name=$ROLE_NAME --region $REGION \
        --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$EC2_NAME},{Key=PROJECT_NAME,Value=$PROJECT_NAME}]" \
        --user-data file://$USER_DATA_FILE \
        --query 'Instances[0].InstanceId' --output text)
    #echo $INSTANCE_ID > $INSTANCE_ID_FILE

    echo "Stack created!"
    echo "S3 bucket: $BUCKET_NAME"
    echo "IAM Role: $ROLE_NAME (attached policy: $POLICY_NAME)"
    echo "Security Group: $SG_NAME ($SG_ID)"
    echo "EC2 Instance: $EC2_NAME ($INSTANCE_ID)"
    echo "Delete temp files manually if non usati."
}

function destroy_stack() {
    echo "Destroying Bedrock/RAG stack in $REGION..."

    # 1. Terminate EC2 instances with PROJECT_NAME tag
    INSTANCE_IDS=$(aws $AWS_PROFILE ec2 describe-instances --region $REGION --filters "Name=tag:PROJECT_NAME,Values=$PROJECT_NAME" "Name=instance-state-name,Values=running,stopped" --query "Reservations[].Instances[].InstanceId" --output text)
    if [ ! -z "$INSTANCE_IDS" ]; then
        echo "Terminating EC2 Instances: $INSTANCE_IDS"
        aws $AWS_PROFILE ec2 terminate-instances --instance-ids $INSTANCE_IDS --region $REGION
    fi

    # 2. Delete Security Groups with PROJECT_NAME tag
    SG_IDS=$(aws $AWS_PROFILE ec2 describe-security-groups --region $REGION --filters "Name=tag:PROJECT_NAME,Values=$PROJECT_NAME" --query "SecurityGroups[].GroupId" --output text)
    for SG_ID in $SG_IDS; do
        if [ ! -z "$SG_ID" ]; then
            echo "Deleting Security Group $SG_ID"
            aws $AWS_PROFILE ec2 delete-security-group --group-id $SG_ID --region $REGION
        fi
    done

    # 3. Delete S3 bucket and its contents
    echo "Deleting S3 bucket: $BUCKET_NAME"
    aws $AWS_PROFILE s3 rm s3://$BUCKET_NAME --recursive
    aws $AWS_PROFILE s3api delete-bucket --bucket $BUCKET_NAME --region $REGION

    # 4. Detach and delete IAM policy, role and instance profile
    echo "Detaching and deleting IAM policy/role/instance profile"
    aws $AWS_PROFILE iam detach-role-policy --role-name $ROLE_NAME --policy-arn arn:aws:iam::$(aws $AWS_PROFILE sts get-caller-identity --query Account --output text):policy/$POLICY_NAME
    aws $AWS_PROFILE iam remove-role-from-instance-profile --instance-profile-name $ROLE_NAME --role-name $ROLE_NAME
    aws $AWS_PROFILE iam delete-instance-profile --instance-profile-name $ROLE_NAME
    aws $AWS_PROFILE iam delete-policy --policy-arn arn:aws:iam::$(aws $AWS_PROFILE sts get-caller-identity --query Account --output text):policy/$POLICY_NAME
    aws $AWS_PROFILE iam delete-role --role-name $ROLE_NAME

    # 5. Delete temp files
    rm -f $ROLE_ARN_FILE /tmp/trust-policy.json

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