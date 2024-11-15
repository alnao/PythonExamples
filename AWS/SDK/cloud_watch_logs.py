import boto3
from botocore.exceptions import ClientError
import logging
import json
from typing import List, Dict, Optional, Union, Generator
from datetime import datetime, timedelta
import time

class AwsCloudWatchLogs:
    """
    A class to manage AWS CloudWatch alarms using boto3
    """
    def __init__(self, profile_name, region_name: str = 'eu-west-1'):
        """
        Initialize CloudWatch client
        
        Args:
            aws_profile: AWS profile name (optional)
            region_name: AWS region name
        """
        self.profile_name=profile_name
        boto3.setup_default_session(profile_name=self.profile_name)
        self.logger = logging.getLogger(__name__)
        session = boto3.Session(profile_name=profile_name, region_name=region_name)
        #self.cloudwatch = session.client('cloudwatch')
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

def main(profile):
    print("Aws Py Console - Aws CloudWatch Logs START")
    print("-----")
    o=AwsCloudWatchLogs(profile)
    l=list(o.list_log_groups())
    for e in l:
        print(e)
        #{'logGroupName': 'API-Gateway-Execution-Logs_pce8v0faz7/dev', 'creationTime': 1724662419623, 
        # 'metricFilterCount': 0, 'arn': 'arn:aws:logs:eu-west-1:740456629644:log-group:API-Gateway-Execution-Logs_pce8v0faz7/dev:*', 
        # 'storedBytes': 550243, 'logGroupClass': 'STANDARD', 'logGroupArn': 'arn:aws:logs:eu-west-1:740456629644:log-group:API-Gateway-Execution-Logs_pce8v0faz7/dev'}
    print("-----")
    if len(l)>0:
        ll=list(o.list_log_streams( l[0]['logGroupName'] ))
        for e in ll:
            print(e)
        print("------")
        if len(ll)>0:
            lll=( o.get_log_events( l[0]['logGroupName'] , ll[0]['logStreamName'] ) )
            #print(lll)
            for e in lll['events']:
                print(e)
    print("-----")
    

if __name__ == '__main__':
    main("default")
