import boto3
from botocore.exceptions import ClientError
from typing import List, Dict, Optional, Union
import logging
import json

class AwsCloudWatchAlarm:
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

def main(profile):
    print("Aws Py Console - Aws CloudWatch Alarms START")
    o=AwsCloudWatchAlarm(profile)
    l=o.list_alarms()
    print(l)
    print("-----")
    if len(l)>0:
        print(l[0])
        h=o.get_alarm_history(l[0]['AlarmName'])
        print(h)
        if len(h)>0:
            print("-----")
            print(h[0])
            history = json.loads( h[0]['HistoryData'] )
            print("-----")
            print(history['oldState'])

#set_alarm_state(self, alarm_name: str, state_value: str, reason: str) 

if __name__ == '__main__':
    main("default")
