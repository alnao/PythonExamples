import boto3
from botocore.exceptions import ClientError
from typing import List, Dict, Optional, Union, Generator
import logging
from datetime import datetime, timedelta
import time

class CloudWatchAlarmManager:
    """
    A class to manage AWS CloudWatch alarms using boto3
    """
    
    def __init__(self, region_name: str = 'eu-west-1', aws_profile: Optional[str] = None):
        """
        Initialize CloudWatch client
        
        Args:
            region_name: AWS region name
            aws_profile: AWS profile name (optional)
        """
        self.logger = logging.getLogger(__name__)
        
        if aws_profile:
            session = boto3.Session(profile_name=aws_profile, region_name=region_name)
        else:
            session = boto3.Session(region_name=region_name)
            
        self.cloudwatch = session.client('cloudwatch')
        
    def create_cpu_alarm(self, 
                        alarm_name: str,
                        asg_name: str,
                        threshold: float,
                        comparison_operator: str = 'GreaterThanThreshold',
                        evaluation_periods: int = 2,
                        period: int = 300,
                        alarm_actions: Optional[List[str]] = None) -> Dict:
        """
        Create a CPU utilization alarm for an Auto Scaling Group
        
        Args:
            alarm_name: Name of the alarm
            asg_name: Name of the Auto Scaling Group
            threshold: The value to compare against
            comparison_operator: How to compare the metric against the threshold
            evaluation_periods: Number of periods before triggering alarm
            period: The period in seconds over which the metric is evaluated
            alarm_actions: List of ARNs to execute when alarm triggers
            
        Returns:
            Dictionary containing the response from AWS
        """
        try:
            response = self.cloudwatch.put_metric_alarm(
                AlarmName=alarm_name,
                AlarmDescription=f'CPU Utilization monitoring for {asg_name}',
                MetricName='CPUUtilization',
                Namespace='AWS/EC2',
                Statistic='Average',
                Dimensions=[
                    {
                        'Name': 'AutoScalingGroupName',
                        'Value': asg_name
                    }
                ],
                Period=period,
                EvaluationPeriods=evaluation_periods,
                Threshold=threshold,
                ComparisonOperator=comparison_operator,
                AlarmActions=alarm_actions or []
            )
            self.logger.info(f"Created alarm {alarm_name} for ASG {asg_name}")
            return response
        except ClientError as e:
            self.logger.error(f"Error creating alarm: {e}")
            raise
            
    def list_alarms(self, state_value: Optional[str] = None) -> List[Dict]:
        """
        List CloudWatch alarms
        
        Args:
            state_value: Filter alarms by state (OK, ALARM, INSUFFICIENT_DATA)
            
        Returns:
            List of alarms
        """
        try:
            if state_value:
                response = self.cloudwatch.describe_alarms(StateValue=state_value)
            else:
                response = self.cloudwatch.describe_alarms()
                
            return response['MetricAlarms']
        except ClientError as e:
            self.logger.error(f"Error listing alarms: {e}")
            raise
            
    def delete_alarms(self, alarm_names: List[str]) -> Dict:
        """
        Delete one or more alarms
        
        Args:
            alarm_names: List of alarm names to delete
            
        Returns:
            AWS response dictionary
        """
        try:
            response = self.cloudwatch.delete_alarms(AlarmNames=alarm_names)
            self.logger.info(f"Deleted alarms: {', '.join(alarm_names)}")
            return response
        except ClientError as e:
            self.logger.error(f"Error deleting alarms: {e}")
            raise
            
    def set_alarm_state(self, 
                       alarm_name: str, 
                       state_value: str, 
                       reason: str) -> Dict:
        """
        Manually set the state of an alarm
        
        Args:
            alarm_name: Name of the alarm
            state_value: New state (OK, ALARM, INSUFFICIENT_DATA)
            reason: Reason for state change
            
        Returns:
            AWS response dictionary
        """
        try:
            response = self.cloudwatch.set_alarm_state(
                AlarmName=alarm_name,
                StateValue=state_value,
                StateReason=reason
            )
            self.logger.info(f"Set alarm {alarm_name} to state {state_value}")
            return response
        except ClientError as e:
            self.logger.error(f"Error setting alarm state: {e}")
            raise
            
    def enable_alarm_actions(self, alarm_names: List[str]) -> Dict:
        """
        Enable actions for specified alarms
        
        Args:
            alarm_names: List of alarm names
            
        Returns:
            AWS response dictionary
        """
        try:
            response = self.cloudwatch.enable_alarm_actions(AlarmNames=alarm_names)
            self.logger.info(f"Enabled actions for alarms: {', '.join(alarm_names)}")
            return response
        except ClientError as e:
            self.logger.error(f"Error enabling alarm actions: {e}")
            raise
            
    def disable_alarm_actions(self, alarm_names: List[str]) -> Dict:
        """
        Disable actions for specified alarms
        
        Args:
            alarm_names: List of alarm names
            
        Returns:
            AWS response dictionary
        """
        try:
            response = self.cloudwatch.disable_alarm_actions(AlarmNames=alarm_names)
            self.logger.info(f"Disabled actions for alarms: {', '.join(alarm_names)}")
            return response
        except ClientError as e:
            self.logger.error(f"Error disabling alarm actions: {e}")
            raise
            
    def get_alarm_history(self, alarm_name: str) -> List[Dict]:
        """
        Get the history for an alarm
        
        Args:
            alarm_name: Name of the alarm
            
        Returns:
            List of historical alarm events
        """
        try:
            response = self.cloudwatch.describe_alarm_history(
                AlarmName=alarm_name
            )
            return response['AlarmHistoryItems']
        except ClientError as e:
            self.logger.error(f"Error getting alarm history: {e}")
            raise


class CloudWatchLogsManager:
    """
    A class to manage AWS CloudWatch Logs using boto3
    """
    
    def __init__(self, region_name: str = 'eu-west-1', aws_profile: Optional[str] = None):
        """
        Initialize CloudWatch Logs client
        
        Args:
            region_name: AWS region name
            aws_profile: AWS profile name (optional)
        """
        self.logger = logging.getLogger(__name__)
        
        if aws_profile:
            session = boto3.Session(profile_name=aws_profile, region_name=region_name)
        else:
            session = boto3.Session(region_name=region_name)
            
        self.logs = session.client('logs')
        
    def create_log_group(self, log_group_name: str, retention_days: int = 30, tags: Optional[Dict] = None) -> Dict:
        """
        Create a new log group
        
        Args:
            log_group_name: Name of the log group
            retention_days: Number of days to retain logs (0 means infinite retention)
            tags: Optional dictionary of tags
            
        Returns:
            AWS response dictionary
        """
        try:
            response = self.logs.create_log_group(
                logGroupName=log_group_name
            )
            
            if retention_days > 0:
                self.logs.put_retention_policy(
                    logGroupName=log_group_name,
                    retentionInDays=retention_days
                )
                
            if tags:
                self.logs.tag_log_group(
                    logGroupName=log_group_name,
                    tags=tags
                )
                
            self.logger.info(f"Created log group: {log_group_name}")
            return response
        except ClientError as e:
            self.logger.error(f"Error creating log group: {e}")
            raise
            
    def create_log_stream(self, log_group_name: str, log_stream_name: str) -> Dict:
        """
        Create a new log stream in a log group
        
        Args:
            log_group_name: Name of the log group
            log_stream_name: Name of the log stream
            
        Returns:
            AWS response dictionary
        """
        try:
            response = self.logs.create_log_stream(
                logGroupName=log_group_name,
                logStreamName=log_stream_name
            )
            self.logger.info(f"Created log stream: {log_stream_name} in group: {log_group_name}")
            return response
        except ClientError as e:
            self.logger.error(f"Error creating log stream: {e}")
            raise
            
    def put_log_events(self, 
                      log_group_name: str, 
                      log_stream_name: str, 
                      events: List[Dict[str, Union[str, int]]],
                      sequence_token: Optional[str] = None) -> Dict:
        """
        Put log events into a log stream
        
        Args:
            log_group_name: Name of the log group
            log_stream_name: Name of the log stream
            events: List of event dictionaries with 'message' and optional 'timestamp'
            sequence_token: Optional sequence token for consecutive puts
            
        Returns:
            AWS response dictionary including the next sequence token
        """
        try:
            # Ensure events have timestamps
            formatted_events = []
            for event in events:
                if isinstance(event, str):
                    event = {'message': event}
                if 'timestamp' not in event:
                    event['timestamp'] = int(time.time() * 1000)
                formatted_events.append(event)
                
            kwargs = {
                'logGroupName': log_group_name,
                'logStreamName': log_stream_name,
                'logEvents': formatted_events
            }
            
            if sequence_token:
                kwargs['sequenceToken'] = sequence_token
                
            response = self.logs.put_log_events(**kwargs)
            self.logger.info(f"Put {len(events)} log events into {log_stream_name}")
            return response
        except ClientError as e:
            self.logger.error(f"Error putting log events: {e}")
            raise
            
    def get_log_events(self, 
                      log_group_name: str, 
                      log_stream_name: str,
                      start_time: Optional[datetime] = None,
                      end_time: Optional[datetime] = None,
                      limit: Optional[int] = None,
                      next_token: Optional[str] = None) -> Dict:
        """
        Get log events from a log stream
        
        Args:
            log_group_name: Name of the log group
            log_stream_name: Name of the log stream
            start_time: Optional start time for the logs
            end_time: Optional end time for the logs
            limit: Maximum number of events to return
            next_token: Token for pagination
            
        Returns:
            Dictionary containing events and next token
        """
        try:
            kwargs = {
                'logGroupName': log_group_name,
                'logStreamName': log_stream_name,
                'startFromHead': True
            }
            
            if start_time:
                kwargs['startTime'] = int(start_time.timestamp() * 1000)
            if end_time:
                kwargs['endTime'] = int(end_time.timestamp() * 1000)
            if limit:
                kwargs['limit'] = limit
            if next_token:
                kwargs['nextToken'] = next_token
                
            return self.logs.get_log_events(**kwargs)
        except ClientError as e:
            self.logger.error(f"Error getting log events: {e}")
            raise
            
    def filter_log_events(self,
                         log_group_name: str,
                         filter_pattern: str,
                         start_time: Optional[datetime] = None,
                         end_time: Optional[datetime] = None,
                         limit: Optional[int] = None) -> Generator:
        """
        Filter log events across all streams in a group
        
        Args:
            log_group_name: Name of the log group
            filter_pattern: CloudWatch Logs filter pattern
            start_time: Optional start time for the logs
            end_time: Optional end time for the logs
            limit: Maximum number of events to return
            
        Yields:
            Log events matching the filter
        """
        try:
            kwargs = {
                'logGroupName': log_group_name,
                'filterPattern': filter_pattern
            }
            
            if start_time:
                kwargs['startTime'] = int(start_time.timestamp() * 1000)
            if end_time:
                kwargs['endTime'] = int(end_time.timestamp() * 1000)
            if limit:
                kwargs['limit'] = limit
                
            paginator = self.logs.get_paginator('filter_log_events')
            
            for page in paginator.paginate(**kwargs):
                for event in page.get('events', []):
                    yield event
        except ClientError as e:
            self.logger.error(f"Error filtering log events: {e}")
            raise
            
    def delete_log_group(self, log_group_name: str) -> Dict:
        """
        Delete a log group and all its log streams
        
        Args:
            log_group_name: Name of the log group
            
        Returns:
            AWS response dictionary
        """
        try:
            response = self.logs.delete_log_group(
                logGroupName=log_group_name
            )
            self.logger.info(f"Deleted log group: {log_group_name}")
            return response
        except ClientError as e:
            self.logger.error(f"Error deleting log group: {e}")
            raise
            
    def delete_log_stream(self, log_group_name: str, log_stream_name: str) -> Dict:
        """
        Delete a log stream
        
        Args:
            log_group_name: Name of the log group
            log_stream_name: Name of the log stream
            
        Returns:
            AWS response dictionary
        """
        try:
            response = self.logs.delete_log_stream(
                logGroupName=log_group_name,
                logStreamName=log_stream_name
            )
            self.logger.info(f"Deleted log stream: {log_stream_name} from group: {log_group_name}")
            return response
        except ClientError as e:
            self.logger.error(f"Error deleting log stream: {e}")
            raise
            
    def list_log_groups(self, prefix: Optional[str] = None) -> Generator:
        """
        List all log groups
        
        Args:
            prefix: Optional prefix to filter log groups
            
        Yields:
            Log group information
        """
        try:
            paginator = self.logs.get_paginator('describe_log_groups')
            kwargs = {}
            if prefix:
                kwargs['logGroupNamePrefix'] = prefix
                
            for page in paginator.paginate(**kwargs):
                for group in page.get('logGroups', []):
                    yield group
        except ClientError as e:
            self.logger.error(f"Error listing log groups: {e}")
            raise
            
    def list_log_streams(self, 
                        log_group_name: str, 
                        prefix: Optional[str] = None,
                        orderBy: str = 'LogStreamName',
                        descending: bool = False) -> Generator:
        """
        List all log streams in a log group
        
        Args:
            log_group_name: Name of the log group
            prefix: Optional prefix to filter log streams
            orderBy: Order by 'LogStreamName' or 'LastEventTime'
            descending: Whether to order in descending order
            
        Yields:
            Log stream information
        """
        try:
            paginator = self.logs.get_paginator('describe_log_streams')
            kwargs = {
                'logGroupName': log_group_name,
                'orderBy': orderBy,
                'descending': descending
            }
            if prefix:
                kwargs['logStreamNamePrefix'] = prefix
                
            for page in paginator.paginate(**kwargs):
                for stream in page.get('logStreams', []):
                    yield stream
        except ClientError as e:
            self.logger.error(f"Error listing log streams: {e}")
            raise