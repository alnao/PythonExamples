#!/bin/bash
# Bootstrap CDK dell'account con i nomi e i tag del repository (vedi README.md):
#   bucket degli asset e repository ECR "alnao-dev-cdk", versione in SSM "/cdk-bootstrap/alnao/dev/version",
#   qualifier "alnaodev" (ruoli cdk-alnaodev-*), stack CloudFormation "CDKToolkit".
#
# Example usage:
# ./bootstrap.sh                          # chiede azione e region mostrando i default
# ./bootstrap.sh create eu-central-1      # crea (o aggiorna) il bootstrap nella region
# ./bootstrap.sh destroy eu-central-1     # toglie tutto il bootstrap dalla region (anche quello di default)

set -euo pipefail
export AWS_PAGER=""   # Disabilita paginazione aws cli
cd "$(dirname "$0")"

# Valori usati anche dal DefaultStackSynthesizer negli app.py dei progetti CDK
NAME="alnao-dev-cdk"
QUALIFIER="alnaodev"
VERSION_PARAMETER="/cdk-bootstrap/alnao/dev/version"
TOOLKIT_STACK="CDKToolkit"
CDK=${CDK:-cdk}             # es: CDK="npx aws-cdk"
PYTHON=${PYTHON:-python3}

# Chiede un valore mostrando il default (solo da terminale; altrimenti usa il default)
function ask() {
    local var=$1 prompt=$2 default=$3 value=""
    if [ -t 0 ]; then
        read -r -p "$prompt [$default]: " value
    fi
    printf -v "$var" '%s' "${value:-$default}"
}

# Conferma da terminale (senza terminale si procede)
function confirm() {
    if [ -t 0 ]; then
        read -r -p "$1 [s/N]: " CONFIRM
        [[ "$CONFIRM" =~ ^[sSyY]$ ]] || { echo "Annullato."; exit 0; }
    fi
}

ACTION=${1:-}
REGION=${2:-}
[ -z "$ACTION" ] && ask ACTION "Azione (create | destroy)" "create"
if [[ "$ACTION" != "create" && "$ACTION" != "destroy" ]]; then
    echo "Usage: $0 create|destroy [REGION]"
    exit 1
fi
[ -z "$REGION" ] && ask REGION "Region" "eu-central-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

function create_bootstrap() {
    echo "Account: $ACCOUNT_ID | Region: $REGION | Bucket e ECR: $NAME | SSM: $VERSION_PARAMETER | Qualifier: $QUALIFIER"
    confirm "Procedo con il bootstrap?"

    WORK_DIR=$(mktemp -d)
    trap 'rm -rf "$WORK_DIR"' EXIT

    # Template ufficiale della versione di CDK installata, adattato ai nomi del repository
    $CDK bootstrap --show-template > "$WORK_DIR/original.yaml"
    $PYTHON patch_template.py "$WORK_DIR/original.yaml" "$WORK_DIR/template.yaml" "$NAME" "$QUALIFIER" "$VERSION_PARAMETER"

    # Tag standard del repository: vanno sullo stack e da li' su bucket, ECR, ruoli e parametro
    $CDK bootstrap "aws://$ACCOUNT_ID/$REGION" \
        --template "$WORK_DIR/template.yaml" \
        --qualifier "$QUALIFIER" \
        --bootstrap-bucket-name "$NAME" \
        --tags Name=aws-py-CDK.bootstrap \
        --tags Environment=dev \
        --tags Project=Development.aws.py-CDK.bootstrap \
        --tags Owner=AlNao \
        --tags CostCenter=dev \
        --tags ManagedBy=CDK

    echo "Bootstrap completato: verifica con"
    echo "  aws ssm get-parameter --name $VERSION_PARAMETER --region $REGION --query Parameter.Value --output text"
}

# Svuota un bucket versionato (versioni e delete marker, 1000 alla volta) e lo cancella
function delete_versioned_bucket() {
    local bucket=$1 objects
    if ! aws s3api head-bucket --bucket "$bucket" --region "$REGION" 2>/dev/null; then
        echo "Bucket $bucket not found or already deleted."
        return
    fi
    echo "Emptying and deleting bucket $bucket..."
    while true; do
        objects=$(aws s3api list-object-versions --bucket "$bucket" --region "$REGION" --max-items 1000 \
            --query '{Objects: [Versions, DeleteMarkers][][].{Key: Key, VersionId: VersionId}, Quiet: `true`}' --output json)
        echo "$objects" | grep -q '"Key"' || break
        aws s3api delete-objects --bucket "$bucket" --region "$REGION" --delete "$objects" >/dev/null
    done
    aws s3api delete-bucket --bucket "$bucket" --region "$REGION"
}

# Toglie dalla region lo stack CDKToolkit e le risorse che sopravvivono alla sua cancellazione
function destroy_bootstrap() {
    if ! aws cloudformation describe-stacks --stack-name $TOOLKIT_STACK --region "$REGION" >/dev/null 2>&1; then
        echo "Stack $TOOLKIT_STACK not found in $REGION: nothing to delete."
        exit 0
    fi
    # nomi letti dallo stack: funziona sia con questo bootstrap sia con quello di default (cdk-hnb659fds-...)
    BUCKET=$(aws cloudformation describe-stacks --stack-name $TOOLKIT_STACK --region "$REGION" \
        --query "Stacks[0].Outputs[?OutputKey=='BucketName'].OutputValue" --output text)
    REPOSITORY=$(aws cloudformation describe-stacks --stack-name $TOOLKIT_STACK --region "$REGION" \
        --query "Stacks[0].Outputs[?OutputKey=='ImageRepositoryName'].OutputValue" --output text)

    echo "Account: $ACCOUNT_ID | Region: $REGION | Stack: $TOOLKIT_STACK | Bucket: $BUCKET | ECR: $REPOSITORY"
    echo "Attenzione: gli stack CDK ancora presenti in $REGION non si potranno piu' aggiornare ne' cancellare"
    echo "con cdk finche' non si rifa' il bootstrap (i loro ruoli di deploy vengono cancellati)."
    confirm "Cancello il bootstrap e tutti gli asset caricati?"

    # 1. ECR: un repository con immagini blocca la cancellazione dello stack, lo si svuota prima
    if [ -n "$REPOSITORY" ] && [ "$REPOSITORY" != "None" ]; then
        IMAGES=$(aws ecr list-images --repository-name "$REPOSITORY" --region "$REGION" --query "length(imageIds)" --output text 2>/dev/null || echo 0)
        if [ "$IMAGES" != "0" ]; then
            echo "Deleting ECR repository $REPOSITORY with $IMAGES images..."
            aws ecr delete-repository --repository-name "$REPOSITORY" --force --region "$REGION" >/dev/null
        fi
    fi

    # 2. Stack: ruoli, parametro SSM, policy e repository ECR (se vuoto) vengono cancellati con lui
    echo "Deleting stack $TOOLKIT_STACK..."
    aws cloudformation delete-stack --stack-name $TOOLKIT_STACK --region "$REGION"
    aws cloudformation wait stack-delete-complete --stack-name $TOOLKIT_STACK --region "$REGION"

    # 3. Bucket degli asset: ha DeletionPolicy Retain, resta dopo lo stack
    if [ -n "$BUCKET" ] && [ "$BUCKET" != "None" ]; then
        delete_versioned_bucket "$BUCKET"
    fi
    echo "✅ Bootstrap removed from $REGION."
}

case "$ACTION" in
    create) create_bootstrap ;;
    destroy) destroy_bootstrap ;;
esac
