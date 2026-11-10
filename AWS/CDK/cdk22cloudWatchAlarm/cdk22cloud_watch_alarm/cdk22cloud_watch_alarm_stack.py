"""Allarmi CloudWatch sull'infrastruttura WordPress del cdk21.

Lo stack estende quello del cdk21 (come l'esempio 22 CloudFormation usava il 21 come stack annidato)
e aggiunge:
- due allarmi sulla CPU media dell'Auto Scaling group che aggiungono o tolgono un server
- due allarmi sulla salute del sito (server malati nel target group, errori 5xx del load balancer)
- un topic SNS che riceve le notifiche (con una email facoltativa: -c alarm_email=...)
- una dashboard CloudWatch con i grafici e lo stato degli allarmi
"""

import os
import sys

from aws_cdk import (
    CfnOutput,
    Duration,
    aws_autoscaling as autoscaling,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cw_actions,
    aws_elasticloadbalancingv2 as elbv2,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions,
)
from constructs import Construct

# lo stack di base e' quello del progetto cdk21autoScalingWordpress, nella cartella accanto
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "cdk21autoScalingWordpress"))
from cdk21auto_scaling_wordpress.cdk21auto_scaling_wordpress_stack import Cdk21AutoScalingWordpressStack  # noqa: E402

CPU_HIGH = 84  # % di CPU media oltre la quale si aggiunge un server
CPU_LOW = 42   # % di CPU media sotto la quale si toglie un server


class Cdk22CloudWatchAlarmStack(Cdk21AutoScalingWordpressStack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        prefix = self.stack_name

        # Topic SNS delle notifiche, email facoltativa da confermare con il link che arriva
        topic = sns.Topic(self, "AlarmTopic", topic_name=f"{prefix}-Alarms", display_name="Allarmi WordPress cdk22")
        email = self.node.try_get_context("alarm_email")
        if email:
            topic.add_subscription(subscriptions.EmailSubscription(email))
        notify = cw_actions.SnsAction(topic)

        # CPU media di tutti i server dell'Auto Scaling group, su periodi di 5 minuti
        cpu = cloudwatch.Metric(namespace="AWS/EC2", metric_name="CPUUtilization",
                                dimensions_map={"AutoScalingGroupName": self.asg.auto_scaling_group_name},
                                statistic=cloudwatch.Stats.AVERAGE, period=Duration.minutes(5))

        # Scaling a passi: +1 server sopra la soglia alta, -1 sotto la soglia bassa
        scale_up = autoscaling.StepScalingAction(self, "CpuScaleUpPolicy", auto_scaling_group=self.asg,
                                                 adjustment_type=autoscaling.AdjustmentType.CHANGE_IN_CAPACITY,
                                                 estimated_instance_warmup=Duration.minutes(5))
        scale_up.add_adjustment(adjustment=1, lower_bound=0)
        scale_down = autoscaling.StepScalingAction(self, "CpuScaleDownPolicy", auto_scaling_group=self.asg,
                                                   adjustment_type=autoscaling.AdjustmentType.CHANGE_IN_CAPACITY,
                                                   estimated_instance_warmup=Duration.minutes(5))
        scale_down.add_adjustment(adjustment=-1, upper_bound=0)

        self.cpu_high = cloudwatch.Alarm(self, "CpuAlarmHigh", alarm_name=f"{prefix}-CpuHigh", metric=cpu,
            threshold=CPU_HIGH, evaluation_periods=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            alarm_description=f"Scale-up se la CPU media supera il {CPU_HIGH}% per 10 minuti")
        self.cpu_high.add_alarm_action(cw_actions.AutoScalingAction(scale_up), notify)
        self.cpu_high.add_ok_action(notify)

        self.cpu_low = cloudwatch.Alarm(self, "CpuAlarmLow", alarm_name=f"{prefix}-CpuLow", metric=cpu,
            threshold=CPU_LOW, evaluation_periods=2,
            comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
            alarm_description=f"Scale-down se la CPU media resta sotto il {CPU_LOW}% per 10 minuti")
        self.cpu_low.add_alarm_action(cw_actions.AutoScalingAction(scale_down))

        # Salute del sito: almeno un server malato per 3 minuti di fila
        unhealthy = self.target_group.metrics.unhealthy_host_count(period=Duration.minutes(1),
                                                                    statistic=cloudwatch.Stats.MAXIMUM)
        self.unhealthy_alarm = cloudwatch.Alarm(self, "UnhealthyHostsAlarm", alarm_name=f"{prefix}-UnhealthyHosts",
            metric=unhealthy, threshold=1, evaluation_periods=3,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
            alarm_description="Almeno un server WordPress non risponde al controllo di salute da 3 minuti")
        self.unhealthy_alarm.add_alarm_action(notify)
        self.unhealthy_alarm.add_ok_action(notify)

        # Errori 5xx generati dal load balancer (nessun server sano, timeout, ...)
        errors = self.alb.metrics.http_code_elb(elbv2.HttpCodeElb.ELB_5XX_COUNT, period=Duration.minutes(5),
                                                statistic=cloudwatch.Stats.SUM)
        self.errors_alarm = cloudwatch.Alarm(self, "LoadBalancer5xxAlarm", alarm_name=f"{prefix}-LoadBalancer5xx",
            metric=errors, threshold=10, evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
            alarm_description="Piu' di 10 errori 5xx del load balancer in 5 minuti")
        self.errors_alarm.add_alarm_action(notify)

        # Dashboard: CPU con le soglie, server in servizio, richieste ed errori, stato degli allarmi
        in_service = cloudwatch.Metric(namespace="AWS/AutoScaling", metric_name="GroupInServiceInstances",
                                       dimensions_map={"AutoScalingGroupName": self.asg.auto_scaling_group_name},
                                       statistic=cloudwatch.Stats.AVERAGE, period=Duration.minutes(1))
        dashboard = cloudwatch.Dashboard(self, "Dashboard", dashboard_name=f"{prefix}-WordPress",
                                         default_interval=Duration.hours(3))
        dashboard.add_widgets(
            cloudwatch.AlarmStatusWidget(title="Allarmi", width=24, height=3,
                alarms=[self.cpu_high, self.cpu_low, self.unhealthy_alarm, self.errors_alarm]))
        dashboard.add_widgets(
            cloudwatch.GraphWidget(title="CPU media (%)", width=12, left=[cpu],
                left_annotations=[cloudwatch.HorizontalAnnotation(value=CPU_HIGH, label="scale-up"),
                                  cloudwatch.HorizontalAnnotation(value=CPU_LOW, label="scale-down")]),
            cloudwatch.GraphWidget(title="Server in servizio", width=12, left=[in_service]),
        )
        dashboard.add_widgets(
            cloudwatch.GraphWidget(title="Richieste al load balancer", width=12,
                left=[self.alb.metrics.request_count(period=Duration.minutes(5))]),
            cloudwatch.GraphWidget(title="Server malati ed errori 5xx", width=12, left=[unhealthy], right=[errors]),
        )

        CfnOutput(self, "AlarmTopicArn", value=topic.topic_arn)
        CfnOutput(self, "CpuAlarmHighName", value=self.cpu_high.alarm_name)
        CfnOutput(self, "DashboardUrl",
                  value=f"https://{self.region}.console.aws.amazon.com/cloudwatch/home?region={self.region}"
                        f"#dashboards/dashboard/{prefix}-WordPress")
