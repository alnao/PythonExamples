"""
Risorse gestite da CloudFormation: stack delle region scelte e risorse di ogni stack.

    - describe_stacks per region (solo gli stack non cancellati, nested compresi)
    - list_stack_resources per stack, in parallelo
    - i tag delle risorse vengono dalla Resource Groups Tagging API (la sezione passa la
      lettura con la cache del Tag Manager): CloudFormation mette su ogni risorsa taggabile che crea i tag
      aws:cloudformation:stack-id e aws:cloudformation:logical-id, che legano la risorsa
      del Tagging API alla riga dello stack (con il suo ARN). Una risorsa che non compare
      non ha tag (tipo senza tag, o region dei tag non letta)

Tutte letture gratuite (describe/list).
"""

import logging

from common import GLOBAL_REGION, aws_session, run_parallel

logger = logging.getLogger(__name__)

STACK_ID_TAG = 'aws:cloudformation:stack-id'
LOGICAL_ID_TAG = 'aws:cloudformation:logical-id'


def _stacks(profile, region):
    client = aws_session(profile, region).client('cloudformation')
    out = []
    for page in client.get_paginator('describe_stacks').paginate():
        for s in page.get('Stacks', []):
            out.append({
                'name': s['StackName'], 'id': s['StackId'], 'region': region,
                'status': s['StackStatus'], 'reason': s.get('StackStatusReason', ''),
                'created': s.get('CreationTime'), 'updated': s.get('LastUpdatedTime'),
                'description': s.get('Description', ''),
                'parent': s.get('ParentId', ''), 'root': s.get('RootId', ''),
                'drift': (s.get('DriftInformation') or {}).get('StackDriftStatus', ''),
                'protection': bool(s.get('EnableTerminationProtection')),
                'tags': {t['Key']: t['Value'] for t in s.get('Tags', [])},
            })
    return out


def _stack_resources(profile, stack):
    client = aws_session(profile, stack['region']).client('cloudformation')
    out = []
    for page in client.get_paginator('list_stack_resources').paginate(StackName=stack['id']):
        out.extend(page.get('StackResourceSummaries', []))
    return out


def _tag_index(regions, tagged_resources):
    """
    {(stack-id, logical-id): (arn, tags)} dai tag automatici di CloudFormation.
    tagged_resources(region) -> [{'arn', 'tags'}]. Ritorna anche le region lette e gli
    avvisi di quelle non leggibili.
    """
    index, read, warnings = {}, set(), []
    for r, res, err in run_parallel(regions, tagged_resources):
        if err:
            warnings.append(f"tag {r}: {err}")
            continue
        read.add(r)
        for item in res:
            tags = item.get('tags') or {}
            if STACK_ID_TAG in tags and LOGICAL_ID_TAG in tags:
                index[(tags[STACK_ID_TAG], tags[LOGICAL_ID_TAG])] = (item['arn'], tags)
    return index, read, warnings


def _region(arn, stack_region):
    """Region dall'ARN; 'global' se l'ARN non ne ha (IAM, CloudFront), tranne S3 (bucket regionali)."""
    parts = arn.split(':')
    if len(parts) < 4:
        return stack_region
    if parts[3]:
        return parts[3]
    return stack_region if parts[2] == 's3' else 'global'


def collect(profile, regions, tagged_resources):
    """
    tagged_resources(region) -> [{'arn', 'tags'}] dalla Tagging API.
    Ritorna {'stacks': [...], 'resources': [...], 'warnings': [...]}.
    Ogni risorsa: {logical_id, physical_id, type, status, reason, drift, updated, arn, region,
                   tags, tagged, stack, stack_id, stack_region, nested}.
    """
    warnings = []
    stacks = []
    for r, res, err in run_parallel(regions, lambda r: _stacks(profile, r)):
        if err:
            warnings.append(f"{r}: {err}")
        else:
            stacks += res

    # tag: le region degli stack piu' us-east-1, dove stanno quelli delle risorse globali
    tag_regions = list(dict.fromkeys(list(regions) + [GLOBAL_REGION]))
    index, tags_read, tag_warnings = _tag_index(tag_regions, tagged_resources)
    warnings += tag_warnings

    by_id = {s['id']: s for s in stacks}
    resources = []
    for stack, res, err in run_parallel(stacks, lambda s: _stack_resources(profile, s)):
        if err:
            stack['error'] = err
            stack['resources'] = 0
            continue
        stack['error'] = None
        stack['resources'] = len(res)
        for x in res:
            arn, tags = index.get((stack['id'], x['LogicalResourceId']), ('', None))
            child = by_id.get(x.get('PhysicalResourceId')) if x['ResourceType'] == 'AWS::CloudFormation::Stack' else None
            if child and tags is None:
                # stack nested: tag e ARN dello stack figlio (describe_stacks)
                arn, tags = child['id'], child['tags']
            resources.append({
                'logical_id': x['LogicalResourceId'], 'physical_id': x.get('PhysicalResourceId', ''),
                'type': x['ResourceType'], 'status': x.get('ResourceStatus', ''),
                'reason': x.get('ResourceStatusReason', ''),
                'drift': (x.get('DriftInformation') or {}).get('StackResourceDriftStatus', ''),
                'updated': x.get('LastUpdatedTimestamp'),
                'arn': arn, 'region': _region(arn, stack['region']) if arn else stack['region'],
                'tags': tags or {}, 'tagged': tags is not None,
                'stack': stack['name'], 'stack_id': stack['id'], 'stack_region': stack['region'],
                'nested': bool(stack['parent']),
            })
    return {'stacks': stacks, 'resources': resources, 'warnings': warnings,
            'tag_regions': sorted(tags_read)}
