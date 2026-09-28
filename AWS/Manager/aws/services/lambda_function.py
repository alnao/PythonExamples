"""Lambda: funzioni, configurazione, invocazioni delle ultime 24 ore e ultimi log."""

from datetime import datetime, timedelta, timezone

from botocore.exceptions import ClientError

from aws.services import paginate


class AwsLambda:
    def __init__(self, session):
        self.client = session.client('lambda')
        self.cloudwatch = session.client('cloudwatch')
        self.logs = session.client('logs')

    def functions(self):
        return paginate(self.client, 'list_functions', 'Functions')

    def configuration(self, name):
        return self.client.get_function_configuration(FunctionName=name)

    def invocations(self, name, hours=24):
        """Invocazioni ora per ora (metrica AWS/Lambda Invocations, somma)."""
        end = datetime.now(timezone.utc)
        datapoints = self.cloudwatch.get_metric_statistics(
            Namespace='AWS/Lambda', MetricName='Invocations',
            Dimensions=[{'Name': 'FunctionName', 'Value': name}],
            StartTime=end - timedelta(hours=hours), EndTime=end,
            Period=3600, Statistics=['Sum'], Unit='Count').get('Datapoints', [])
        return sorted(datapoints, key=lambda d: d['Timestamp'], reverse=True)

    def last_logs(self, name, limit=100, streams=5):
        """Ultimi eventi del log group /aws/lambda/<nome>, dagli stream piu' recenti."""
        group = f"/aws/lambda/{name}"
        try:
            found = self.logs.describe_log_streams(logGroupName=group, orderBy='LastEventTime',
                                                   descending=True, limit=streams).get('logStreams', [])
        except ClientError as e:
            if e.response.get('Error', {}).get('Code') == 'ResourceNotFoundException':
                return []
            raise
        events = []
        for stream in found:
            events += self.logs.get_log_events(logGroupName=group, logStreamName=stream['logStreamName'],
                                               startFromHead=False, limit=limit).get('events', [])
        return sorted(events, key=lambda e: e['timestamp'], reverse=True)[:limit]
