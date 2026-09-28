"""
Gestione di CloudWatch Alarms e CloudWatch Logs con boto3 (ex ManagerFlaskCloudWatch).

Usata dalla sezione CloudWatch e dalle voci CWAlarms e CWLogs del Manager.
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class CloudWatchAlarmManager:
    """Allarmi CloudWatch di una region."""

    def __init__(self, session):
        """session: sessione boto3 gia' legata a profilo e region (vedi common.aws_session)."""
        self.cloudwatch = session.client('cloudwatch')

    def create_cpu_alarm(self, alarm_name: str, asg_name: str, threshold: float,
                         comparison_operator: str = 'GreaterThanThreshold',
                         evaluation_periods: int = 2, period: int = 300,
                         alarm_actions: Optional[List[str]] = None) -> Dict:
        """Crea un allarme sulla CPU media di un Auto Scaling Group."""
        response = self.cloudwatch.put_metric_alarm(
            AlarmName=alarm_name,
            AlarmDescription=f'CPU Utilization monitoring for {asg_name}',
            MetricName='CPUUtilization',
            Namespace='AWS/EC2',
            Statistic='Average',
            Dimensions=[{'Name': 'AutoScalingGroupName', 'Value': asg_name}],
            Period=period,
            EvaluationPeriods=evaluation_periods,
            Threshold=threshold,
            ComparisonOperator=comparison_operator,
            AlarmActions=alarm_actions or [],
        )
        logger.info(f"Creato l'allarme {alarm_name} per l'ASG {asg_name}")
        return response

    def list_alarms(self, state_value: Optional[str] = None) -> List[Dict]:
        """Allarmi della region, eventualmente solo quelli in uno stato (OK, ALARM, INSUFFICIENT_DATA)."""
        kwargs = {'StateValue': state_value} if state_value else {}
        alarms = []
        for page in self.cloudwatch.get_paginator('describe_alarms').paginate(**kwargs):
            alarms.extend(page.get('MetricAlarms', []))
        return alarms

    def delete_alarms(self, alarm_names: List[str]) -> Dict:
        return self.cloudwatch.delete_alarms(AlarmNames=alarm_names)

    def set_alarm_state(self, alarm_name: str, state_value: str, reason: str) -> Dict:
        """Forza lo stato di un allarme (torna al valore reale alla valutazione successiva)."""
        return self.cloudwatch.set_alarm_state(AlarmName=alarm_name, StateValue=state_value,
                                               StateReason=reason)

    def enable_alarm_actions(self, alarm_names: List[str]) -> Dict:
        return self.cloudwatch.enable_alarm_actions(AlarmNames=alarm_names)

    def disable_alarm_actions(self, alarm_names: List[str]) -> Dict:
        return self.cloudwatch.disable_alarm_actions(AlarmNames=alarm_names)

    def get_alarm_history(self, alarm_name: str) -> List[Dict]:
        """
        Storico dell'allarme. HistoryData e' un JSON: se ne estraggono lo stato di
        partenza e quello di arrivo (oldState/newState) per la tabella.
        """
        items = self.cloudwatch.describe_alarm_history(AlarmName=alarm_name).get('AlarmHistoryItems', [])
        for item in items:
            try:
                data = json.loads(item.get('HistoryData') or '{}')
            except json.JSONDecodeError:
                data = {}
            old, new = data.get('oldState', {}), data.get('newState', {})
            item['OldState'] = old.get('stateValue', '') if isinstance(old, dict) else str(old)
            item['NewState'] = new.get('stateValue', '') if isinstance(new, dict) else str(new)
        return items


class CloudWatchLogsManager:
    """Log group, stream ed eventi di CloudWatch Logs di una region."""

    def __init__(self, session):
        self.logs = session.client('logs')

    def create_log_group(self, log_group_name: str, retention_days: int = 30,
                         tags: Optional[Dict] = None) -> Dict:
        """Crea un log group; retention_days 0 = conservazione illimitata."""
        response = self.logs.create_log_group(logGroupName=log_group_name)
        if retention_days > 0:
            self.logs.put_retention_policy(logGroupName=log_group_name, retentionInDays=retention_days)
        if tags:
            self.logs.tag_log_group(logGroupName=log_group_name, tags=tags)
        logger.info(f"Creato il log group {log_group_name}")
        return response

    def create_log_stream(self, log_group_name: str, log_stream_name: str) -> Dict:
        return self.logs.create_log_stream(logGroupName=log_group_name, logStreamName=log_stream_name)

    def put_log_events(self, log_group_name: str, log_stream_name: str, messages: List[str]) -> Dict:
        """Scrive uno o piu' messaggi nello stream, con il timestamp di adesso."""
        now = int(time.time() * 1000)
        events = [{'timestamp': now, 'message': m} for m in messages]
        return self.logs.put_log_events(logGroupName=log_group_name, logStreamName=log_stream_name,
                                        logEvents=events)

    def get_log_events(self, log_group_name: str, log_stream_name: str, limit: int = 100,
                       start_time: Optional[datetime] = None) -> List[Dict]:
        """Ultimi eventi dello stream, dal piu' recente."""
        kwargs = {'logGroupName': log_group_name, 'logStreamName': log_stream_name,
                  'startFromHead': False, 'limit': limit}
        if start_time:
            kwargs['startTime'] = int(start_time.timestamp() * 1000)
        events = self.logs.get_log_events(**kwargs).get('events', [])
        return sorted(events, key=lambda e: e['timestamp'], reverse=True)

    def filter_log_events(self, log_group_name: str, filter_pattern: str,
                          start_time: Optional[datetime] = None, limit: int = 100) -> List[Dict]:
        """Eventi di tutti gli stream del gruppo che corrispondono al pattern (max limit)."""
        kwargs = {'logGroupName': log_group_name, 'filterPattern': filter_pattern}
        if start_time:
            kwargs['startTime'] = int(start_time.timestamp() * 1000)
        events = []
        for page in self.logs.get_paginator('filter_log_events').paginate(**kwargs):
            events.extend(page.get('events', []))
            if len(events) >= limit:
                break
        return sorted(events[:limit], key=lambda e: e['timestamp'], reverse=True)

    def delete_log_group(self, log_group_name: str) -> Dict:
        """Cancella il log group e tutti i suoi stream."""
        return self.logs.delete_log_group(logGroupName=log_group_name)

    def delete_log_stream(self, log_group_name: str, log_stream_name: str) -> Dict:
        return self.logs.delete_log_stream(logGroupName=log_group_name, logStreamName=log_stream_name)

    def list_log_groups(self, prefix: Optional[str] = None) -> List[Dict]:
        kwargs = {'logGroupNamePrefix': prefix} if prefix else {}
        groups = []
        for page in self.logs.get_paginator('describe_log_groups').paginate(**kwargs):
            groups.extend(page.get('logGroups', []))
        return groups

    def list_log_streams(self, log_group_name: str, limit: int = 100) -> List[Dict]:
        """Stream del gruppo, dal piu' recente (ultimo evento)."""
        response = self.logs.describe_log_streams(logGroupName=log_group_name, orderBy='LastEventTime',
                                                  descending=True, limit=min(limit, 50))
        return response.get('logStreams', [])
