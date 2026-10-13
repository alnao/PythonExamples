# Tag standard delle risorse create con gli esempi di AWS/SDK (convenzione in CLAUDE.md)
STANDARD_TAGS = {
    "Name": "aws-py-SDK",
    "Environment": "dev",
    "Project": "Development.aws.py-SDK",
    "Owner": "AlNao",
    "CostCenter": "dev",
    "ManagedBy": "Manual",
}

def tag_dict(tags=None):
    """Tag standard come dizionario {chiave: valore} (SQS, CloudWatch Logs); tags aggiunge o sovrascrive."""
    return {**STANDARD_TAGS, **(tags or {})}

def tag_list(tags=None):
    """Tag standard come lista [{'Key': .., 'Value': ..}] (EC2, SNS, ECR, EFS, SSM, CloudWatch)."""
    return [{'Key': key, 'Value': value} for key, value in tag_dict(tags).items()]
