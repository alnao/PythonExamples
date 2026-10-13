#!/bin/bash

# Example usage:
# ./bedrock_rag_stack.sh                                         # chiede i parametri mostrando i default
# ./bedrock_rag_stack.sh create Bedrock eu-central-1             # porta 80 aperta solo al tuo IP attuale
# ./bedrock_rag_stack.sh create Bedrock eu-central-1 1.2.3.4/32  # porta 80 aperta a un CIDR scelto
# ./bedrock_rag_stack.sh update Bedrock eu-central-1             # ricarica il codice locale sull'istanza
# ./bedrock_rag_stack.sh destroy Bedrock eu-central-1

set -e
export AWS_PAGER=""   # Disabilita paginazione aws cli
cd "$(dirname "$0")"  # i template e il codice sono accanto allo script

# Chiede un valore mostrando il default (solo da terminale; altrimenti usa il default)
function ask() {
    local var=$1 prompt=$2 default=$3 value=""
    if [ -t 0 ]; then
        read -r -p "$prompt [$default]: " value
    fi
    printf -v "$var" '%s' "${value:-$default}"
}

ACTION=$1                           # create | update | destroy
PROJECT_NAME=$2                     # prefisso dei nomi delle risorse e suffisso del tag Name
REGION=$3                           # default Frankfurt
ALLOWED_CIDR=$4                     # chi puo' aprire il sito (default: il tuo IP pubblico)
[ -z "$ACTION" ] && ask ACTION "Azione (create | update | destroy)" "create"
[ -z "$PROJECT_NAME" ] && ask PROJECT_NAME "Nome del progetto" "Bedrock"
[ -z "$REGION" ] && ask REGION "Region" "eu-central-1"
if [[ "$ACTION" != "create" && "$ACTION" != "update" && "$ACTION" != "destroy" ]]; then
    echo "Usage: $0 create|update|destroy [PROJECT_NAME] [REGION] [ALLOWED_CIDR]"
    exit 1
fi
if [ "$ACTION" == "create" ] && [ -z "$ALLOWED_CIDR" ]; then
    ask ALLOWED_CIDR "CIDR che puo' aprire il sito sulla porta 80" "$(curl -s https://checkip.amazonaws.com | tr -d '[:space:]')/32"
fi

# Parameters
AWS_PROFILE=""                      # es: "--profile mio-profilo"
PROJECT_LOWER=$(echo "$PROJECT_NAME" | tr '[:upper:]' '[:lower:]')
BUCKET_NAME="$PROJECT_LOWER-alnao-bucket"   # i nomi dei bucket S3 devono essere minuscoli
ROLE_NAME="$PROJECT_NAME-role"
POLICY_NAME="$PROJECT_NAME-policy"
SG_NAME="$PROJECT_NAME-security-group"
API_KEY_PARAMETER="/$PROJECT_NAME/api-key"
INSTANCE_TYPE="t3.small"            # 2 GB di RAM: ChromaDB + OCR non stanno in una t3.micro
APP_KEY="app/pocket-rag.tar.gz"     # pacchetto del codice nel bucket
SSM_MANAGED_POLICY="arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
# Ubuntu 24.04 LTS, ultima AMI pubblicata da Canonical
AMI_PARAMETER="/aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id"
POLICY_TEMPLATE=./policy.json
USER_DATA_TEMPLATE=./user_data.sh

# Tag standard su tutte le risorse create (convenzione in CLAUDE.md)
TAG_NAME="aws-py-$PROJECT_NAME"
TAG_PROJECT="Development.aws.py-Bedrock"
# formato "Key=..,Value=.. Key=..,Value=.." per --tags di IAM e SSM
TAGS_KV="Key=Name,Value=$TAG_NAME Key=Environment,Value=dev Key=Project,Value=$TAG_PROJECT Key=Owner,Value=AlNao Key=CostCenter,Value=dev Key=ManagedBy,Value=Sh"
# formato "{Key=..,Value=..},{..}" per TagSet=[..] di S3 e Tags=[..] di --tag-specifications EC2
TAGS_LIST="{Key=Name,Value=$TAG_NAME},{Key=Environment,Value=dev},{Key=Project,Value=$TAG_PROJECT},{Key=Owner,Value=AlNao},{Key=CostCenter,Value=dev},{Key=ManagedBy,Value=Sh}"

echo "Azione: $ACTION | Progetto: $PROJECT_NAME | Region: $REGION | Bucket: $BUCKET_NAME | Tag Name: $TAG_NAME"
if [ "$ACTION" == "create" ]; then
    echo "Porta 80 aperta a: $ALLOWED_CIDR"
fi
if [ -t 0 ]; then
    read -r -p "Procedo? [s/N]: " CONFIRM
    [[ "$CONFIRM" =~ ^[sSyY]$ ]] || { echo "Annullato."; exit 0; }
fi

ACCOUNT_ID=$(aws $AWS_PROFILE sts get-caller-identity --query Account --output text)
POLICY_ARN="arn:aws:iam::$ACCOUNT_ID:policy/$POLICY_NAME"

# Impacchetta il codice locale (backend, requirements, sito), lo carica sul bucket e prepara
# un URL prefirmato valido un'ora: l'istanza lo scarica con curl, senza git ne' credenziali
function upload_app() {
    tar czf "$WORK_DIR/pocket-rag.tar.gz" --exclude=__pycache__ backend.py requirements.txt web
    aws $AWS_PROFILE s3 cp "$WORK_DIR/pocket-rag.tar.gz" "s3://$BUCKET_NAME/$APP_KEY" --region $REGION >/dev/null
    APP_URL=$(aws $AWS_PROFILE s3 presign "s3://$BUCKET_NAME/$APP_KEY" --expires-in 3600 --region $REGION)
    echo "Application package uploaded to s3://$BUCKET_NAME/$APP_KEY"
}

# Crea la policy IAM dal template policy.json o, se esiste, ne pubblica una nuova versione
function apply_policy() {
    sed -e "s|__REGION__|$REGION|g" -e "s|__ACCOUNT_ID__|$ACCOUNT_ID|g" \
        -e "s|__BUCKET_NAME__|$BUCKET_NAME|g" -e "s|__API_KEY_PARAMETER__|$API_KEY_PARAMETER|g" \
        $POLICY_TEMPLATE > "$WORK_DIR/policy.json"
    if aws $AWS_PROFILE iam get-policy --policy-arn $POLICY_ARN >/dev/null 2>&1; then
        echo "IAM Policy $POLICY_NAME already exists: updating it with the current template."
        # al massimo 5 versioni: si cancella la piu' vecchia non di default prima di aggiungerne una
        OLD_VERSION=$(aws $AWS_PROFILE iam list-policy-versions --policy-arn $POLICY_ARN \
            --query "sort_by(Versions[?IsDefaultVersion==\`false\`], &CreateDate)[0].VersionId" --output text)
        VERSIONS=$(aws $AWS_PROFILE iam list-policy-versions --policy-arn $POLICY_ARN --query "length(Versions)" --output text)
        if [ "${VERSIONS:-0}" -ge 5 ] && [ "$OLD_VERSION" != "None" ]; then
            aws $AWS_PROFILE iam delete-policy-version --policy-arn $POLICY_ARN --version-id $OLD_VERSION
        fi
        aws $AWS_PROFILE iam create-policy-version --policy-arn $POLICY_ARN --policy-document file://$WORK_DIR/policy.json --set-as-default >/dev/null
    else
        echo "Creating IAM Policy: $POLICY_NAME"
        aws $AWS_PROFILE iam create-policy --policy-name $POLICY_NAME --policy-document file://$WORK_DIR/policy.json --tags $TAGS_KV
    fi
}

# Istanze del progetto (quelle che usano il suo instance profile) negli stati indicati
function find_instances() {
    local states=$1
    aws $AWS_PROFILE ec2 describe-instances --region $REGION \
        --filters "Name=iam-instance-profile.arn,Values=arn:aws:iam::$ACCOUNT_ID:instance-profile/$ROLE_NAME" "Name=instance-state-name,Values=$states" \
        --query "Reservations[].Instances[].InstanceId" --output text 2>/dev/null || echo ""
}

function create_stack() {
    echo "Creating Bedrock/RAG stack in $REGION..."
    WORK_DIR=$(mktemp -d)
    trap 'rm -rf "$WORK_DIR"' EXIT

    # 1. Create S3 bucket if not exists
    if aws $AWS_PROFILE s3api head-bucket --bucket $BUCKET_NAME 2>/dev/null; then
        echo "S3 bucket $BUCKET_NAME already exists. Skipping creation."
    else
        echo "Creating S3 bucket: $BUCKET_NAME"
        aws $AWS_PROFILE s3api create-bucket --bucket $BUCKET_NAME --region $REGION --create-bucket-configuration LocationConstraint=$REGION
        aws $AWS_PROFILE s3api put-bucket-tagging --bucket $BUCKET_NAME --tagging "TagSet=[$TAGS_LIST]"
    fi

    # 2. API key in SSM Parameter Store (SecureString), letta dal backend all'avvio
    if aws $AWS_PROFILE ssm get-parameter --name $API_KEY_PARAMETER --region $REGION >/dev/null 2>&1; then
        echo "API key parameter $API_KEY_PARAMETER already exists. Skipping creation."
    else
        echo "Creating API key parameter: $API_KEY_PARAMETER"
        aws $AWS_PROFILE ssm put-parameter --name $API_KEY_PARAMETER --type SecureString \
            --value "$(openssl rand -hex 24)" --region $REGION --tags $TAGS_KV >/dev/null
    fi

    # 3. IAM Policy dal template policy.json (permessi minimi)
    apply_policy

    # 4. Create IAM Role for EC2 if not exists
    if aws $AWS_PROFILE iam get-role --role-name $ROLE_NAME >/dev/null 2>&1; then
        echo "IAM Role $ROLE_NAME already exists. Skipping creation."
    else
        echo "Creating IAM Role: $ROLE_NAME"
        cat > "$WORK_DIR/trust-policy.json" <<EOF
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
        aws $AWS_PROFILE iam create-role --role-name $ROLE_NAME --assume-role-policy-document file://$WORK_DIR/trust-policy.json --tags $TAGS_KV
    fi
    aws $AWS_PROFILE iam attach-role-policy --role-name $ROLE_NAME --policy-arn $POLICY_ARN || true
    # Session Manager al posto di SSH: nessuna porta 22 aperta e nessuna key pair
    aws $AWS_PROFILE iam attach-role-policy --role-name $ROLE_NAME --policy-arn $SSM_MANAGED_POLICY || true

    # 4.1. Create Instance Profile and add the role to it if not exists
    if aws $AWS_PROFILE iam get-instance-profile --instance-profile-name $ROLE_NAME >/dev/null 2>&1; then
        echo "Instance Profile $ROLE_NAME already exists. Skipping creation."
    else
        echo "Creating Instance Profile: $ROLE_NAME"
        aws $AWS_PROFILE iam create-instance-profile --instance-profile-name $ROLE_NAME --tags $TAGS_KV
        sleep 5
    fi
    if ! aws $AWS_PROFILE iam get-instance-profile --instance-profile-name $ROLE_NAME --query "InstanceProfile.Roles[?RoleName=='$ROLE_NAME']" --output text | grep -q $ROLE_NAME; then
        aws $AWS_PROFILE iam add-role-to-instance-profile --instance-profile-name $ROLE_NAME --role-name $ROLE_NAME
    fi
    echo "Waiting for instance profile to be ready..."
    sleep 10

    # 5. Security Group: solo la porta 80, solo da ALLOWED_CIDR
    if [ -z "$ALLOWED_CIDR" ]; then
        ALLOWED_CIDR="$(curl -s https://checkip.amazonaws.com | tr -d '[:space:]')/32"
    fi
    VPC_ID=$(aws $AWS_PROFILE ec2 describe-vpcs --region $REGION --filters Name=is-default,Values=true --query 'Vpcs[0].VpcId' --output text)
    SG_ID=$(aws $AWS_PROFILE ec2 describe-security-groups --region $REGION --filters Name=group-name,Values=$SG_NAME Name=vpc-id,Values=$VPC_ID --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null)
    if [ "$SG_ID" == "None" ] || [ -z "$SG_ID" ]; then
        echo "Creating Security Group: $SG_NAME"
        SG_ID=$(aws $AWS_PROFILE ec2 create-security-group --group-name $SG_NAME --description "Bedrock RAG SG" --vpc-id $VPC_ID --region $REGION \
            --tag-specifications "ResourceType=security-group,Tags=[$TAGS_LIST]" --query 'GroupId' --output text)
    else
        echo "Security Group $SG_NAME already exists ($SG_ID)."
        # regole delle versioni precedenti dello script (SSH e uvicorn aperti a tutti)
        for PORT in 22 8000 80; do
            aws $AWS_PROFILE ec2 revoke-security-group-ingress --group-id $SG_ID --protocol tcp --port $PORT --cidr 0.0.0.0/0 --region $REGION >/dev/null 2>&1 || true
        done
    fi
    aws $AWS_PROFILE ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 80 --cidr $ALLOWED_CIDR --region $REGION >/dev/null 2>&1 \
        || echo "Port 80 rule for $ALLOWED_CIDR already present"

    # 6. Codice dell'applicazione sul bucket e user data dal template (con l'URL prefirmato)
    upload_app
    APP_URL_SED=$(printf '%s' "$APP_URL" | sed -e 's/[&|\\]/\\&/g')   # & e | sono speciali per sed
    sed -e "s|__REGION__|$REGION|g" -e "s|__BUCKET_NAME__|$BUCKET_NAME|g" \
        -e "s|__API_KEY_PARAMETER__|$API_KEY_PARAMETER|g" -e "s|__APP_URL__|$APP_URL_SED|g" \
        $USER_DATA_TEMPLATE > "$WORK_DIR/user_data.sh"

    # 7. Launch EC2 instance (Ubuntu 24.04, IMDSv2)
    AMI_ID=$(aws $AWS_PROFILE ssm get-parameters --names $AMI_PARAMETER --region $REGION --query 'Parameters[0].Value' --output text)
    echo "Launching EC2 instance $TAG_NAME from AMI $AMI_ID"
    INSTANCE_ID=$(aws $AWS_PROFILE ec2 run-instances --image-id $AMI_ID --count 1 \
        --instance-type $INSTANCE_TYPE \
        --security-group-ids $SG_ID --iam-instance-profile Name=$ROLE_NAME --region $REGION \
        --metadata-options "HttpTokens=required,HttpEndpoint=enabled" \
        --tag-specifications "ResourceType=instance,Tags=[$TAGS_LIST]" "ResourceType=volume,Tags=[$TAGS_LIST]" "ResourceType=network-interface,Tags=[$TAGS_LIST]" \
        --user-data file://$WORK_DIR/user_data.sh \
        --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":20,"VolumeType":"gp3"}}]' \
        --query 'Instances[0].InstanceId' --output text)
    aws $AWS_PROFILE ec2 wait instance-running --instance-ids $INSTANCE_ID --region $REGION
    PUBLIC_IP=$(aws $AWS_PROFILE ec2 describe-instances --instance-ids $INSTANCE_ID --region $REGION --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)

    echo "Stack created!"
    echo "S3 bucket: $BUCKET_NAME"
    echo "IAM Role: $ROLE_NAME (attached policies: $POLICY_NAME, AmazonSSMManagedInstanceCore)"
    echo "Security Group: $SG_NAME ($SG_ID), port 80 open to $ALLOWED_CIDR"
    echo "EC2 Instance: $TAG_NAME ($INSTANCE_ID)"
    echo "Site (ready in a few minutes): http://$PUBLIC_IP"
    echo "API key: aws ssm get-parameter --name $API_KEY_PARAMETER --with-decryption --region $REGION --query Parameter.Value --output text"
    echo "Shell on the instance: aws ssm start-session --target $INSTANCE_ID --region $REGION"
    echo "Code update after local changes: $0 update $PROJECT_NAME $REGION"
}

# Ricarica policy e codice locale sull'istanza accesa con SSM Run Command (niente SSH, niente git)
function update_app() {
    echo "Updating application code of $PROJECT_NAME in $REGION..."
    WORK_DIR=$(mktemp -d)
    trap 'rm -rf "$WORK_DIR"' EXIT
    INSTANCE_ID=$(find_instances running | awk '{print $1}')
    if [ -z "$INSTANCE_ID" ] || [ "$INSTANCE_ID" == "None" ]; then
        echo "No running instance found for $PROJECT_NAME: run '$0 create' first (or start the instance)."
        exit 1
    fi
    apply_policy   # i modelli autorizzati seguono policy.json
    upload_app
    # l'URL prefirmato non contiene virgolette: si puo' inserire cosi' nel JSON dei comandi
    cat > "$WORK_DIR/commands.json" <<END_OF_COMMANDS
{"commands": [
    "set -e",
    "curl -fsSL '$APP_URL' -o /tmp/pocket-rag.tar.gz",
    "rm -rf /opt/pocket-rag/web",
    "tar xzf /tmp/pocket-rag.tar.gz -C /opt/pocket-rag",
    "/opt/pocket-rag/venv/bin/pip install -q -r /opt/pocket-rag/requirements.txt",
    "chown -R ubuntu:ubuntu /opt/pocket-rag",
    "systemctl restart pocket-rag",
    "rm -f /tmp/pocket-rag.tar.gz",
    "echo Pocket RAG updated"
]}
END_OF_COMMANDS
    COMMAND_ID=$(aws $AWS_PROFILE ssm send-command --instance-ids $INSTANCE_ID --document-name AWS-RunShellScript \
        --comment "Pocket RAG code update" --parameters file://$WORK_DIR/commands.json --region $REGION \
        --query Command.CommandId --output text)
    echo "Command $COMMAND_ID sent to $INSTANCE_ID, waiting..."
    aws $AWS_PROFILE ssm wait command-executed --command-id $COMMAND_ID --instance-id $INSTANCE_ID --region $REGION || true
    aws $AWS_PROFILE ssm get-command-invocation --command-id $COMMAND_ID --instance-id $INSTANCE_ID --region $REGION \
        --query '[Status, StandardOutputContent, StandardErrorContent]' --output text
}

function destroy_stack() {
    echo "Destroying Bedrock/RAG stack in $REGION..."

    # 1. Terminate EC2 instances that use the instance profile of this stack
    echo "1. Checking for EC2 instances to terminate..."
    INSTANCE_IDS=$(find_instances pending,running,stopping,stopped)
    if [ ! -z "$INSTANCE_IDS" ] && [ "$INSTANCE_IDS" != "None" ]; then
        echo "Terminating EC2 Instances: $INSTANCE_IDS"
        aws $AWS_PROFILE ec2 terminate-instances --instance-ids $INSTANCE_IDS --region $REGION >/dev/null 2>&1 || echo "Warning: Failed to terminate some instances"
        echo "Waiting for EC2 instances to be terminated..."
        aws $AWS_PROFILE ec2 wait instance-terminated --instance-ids $INSTANCE_IDS --region $REGION 2>/dev/null || echo "Warning: Timeout waiting for instance termination"
    else
        echo "No EC2 instances found to terminate."
    fi

    # 2. Delete the Security Group of this stack (by name)
    echo "2. Checking for Security Groups to delete..."
    SG_IDS=$(aws $AWS_PROFILE ec2 describe-security-groups --region $REGION --filters "Name=group-name,Values=$SG_NAME" --query "SecurityGroups[].GroupId" --output text 2>/dev/null || echo "")
    for SG_ID in $SG_IDS; do
        if [ "$SG_ID" != "None" ]; then
            echo "Deleting Security Group $SG_ID"
            aws $AWS_PROFILE ec2 delete-security-group --group-id $SG_ID --region $REGION 2>/dev/null || echo "Warning: Failed to delete Security Group $SG_ID (might be in use)"
        fi
    done

    # 3. Delete S3 bucket and its contents (documenti, backup dell'indice e pacchetto del codice)
    echo "3. Checking S3 bucket: $BUCKET_NAME"
    if aws $AWS_PROFILE s3api head-bucket --bucket $BUCKET_NAME --region $REGION 2>/dev/null; then
        echo "Deleting S3 bucket contents and bucket: $BUCKET_NAME"
        aws $AWS_PROFILE s3 rm s3://$BUCKET_NAME --recursive 2>/dev/null || echo "Warning: Failed to delete some S3 objects"
        aws $AWS_PROFILE s3api delete-bucket --bucket $BUCKET_NAME --region $REGION 2>/dev/null || echo "Warning: Failed to delete S3 bucket (might not be empty)"
    else
        echo "S3 bucket $BUCKET_NAME not found or already deleted."
    fi

    # 4. Delete the API key parameter
    echo "4. Deleting API key parameter $API_KEY_PARAMETER..."
    aws $AWS_PROFILE ssm delete-parameter --name $API_KEY_PARAMETER --region $REGION 2>/dev/null || echo "Parameter not found or already deleted"

    # 5. Detach and delete IAM policy, role and instance profile
    echo "5. Cleaning up IAM resources..."
    if aws $AWS_PROFILE iam get-role --role-name $ROLE_NAME >/dev/null 2>&1; then
        INLINE_POLICIES=$(aws $AWS_PROFILE iam list-role-policies --role-name $ROLE_NAME --query 'PolicyNames' --output text 2>/dev/null || echo "")
        for POLICY in $INLINE_POLICIES; do
            if [ "$POLICY" != "None" ]; then
                echo "Deleting inline policy: $POLICY"
                aws $AWS_PROFILE iam delete-role-policy --role-name $ROLE_NAME --policy-name $POLICY 2>/dev/null || echo "Warning: Failed to delete inline policy $POLICY"
            fi
        done
        aws $AWS_PROFILE iam detach-role-policy --role-name $ROLE_NAME --policy-arn $POLICY_ARN 2>/dev/null || echo "Managed policy not attached or doesn't exist"
        aws $AWS_PROFILE iam detach-role-policy --role-name $ROLE_NAME --policy-arn $SSM_MANAGED_POLICY 2>/dev/null || echo "SSM policy not attached"
        aws $AWS_PROFILE iam remove-role-from-instance-profile --instance-profile-name $ROLE_NAME --role-name $ROLE_NAME 2>/dev/null || echo "Role not in instance profile or profile doesn't exist"
        echo "Deleting IAM role: $ROLE_NAME"
        aws $AWS_PROFILE iam delete-role --role-name $ROLE_NAME 2>/dev/null || echo "Warning: Failed to delete role $ROLE_NAME"
    else
        echo "IAM Role $ROLE_NAME not found or already deleted."
    fi
    aws $AWS_PROFILE iam delete-instance-profile --instance-profile-name $ROLE_NAME 2>/dev/null || echo "Instance profile doesn't exist or already deleted"
    aws $AWS_PROFILE iam delete-policy --policy-arn $POLICY_ARN 2>/dev/null || echo "Managed policy doesn't exist or already deleted"

    echo "✅ Stack destruction completed!"
    echo "Note: Some warnings above are normal if resources were already deleted."
}

case "$ACTION" in
    create) create_stack ;;
    update) update_app ;;
    destroy) destroy_stack ;;
esac
