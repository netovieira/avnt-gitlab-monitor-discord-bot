import boto3
from botocore.exceptions import ClientError, ProfileNotFound
from datetime import datetime, timedelta

class AWSResourceManager:
    def __init__(self, aws_access_key, aws_secret_key, aws_region):
        self.session = boto3.Session(
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=aws_region
        )
        self.ecs_client = self.session.client('ecs')
        self.rds_client = self.session.client('rds')
        self.cloudwatch_client = self.session.client('cloudwatch')

    def get_ecs_info(self):
        clusters = self.ecs_client.list_clusters()['clusterArns']
        ecs_info = []

        for cluster_arn in clusters:
            cluster_name = cluster_arn.split('/')[-1]
            services = self.ecs_client.list_services(cluster=cluster_name)['serviceArns']
            
            for service_arn in services:
                service_name = service_arn.split('/')[-1]
                service = self.ecs_client.describe_services(cluster=cluster_name, services=[service_name])['services'][0]
                tasks_count = service['runningCount']
                last_update = service['deployments'][0]['updatedAt']

                cpu_metric = self.get_cloudwatch_metric('AWS/ECS', 'CPUUtilization', 
                                                        [{'Name': 'ClusterName', 'Value': cluster_name},
                                                         {'Name': 'ServiceName', 'Value': service_name}])
                mem_metric = self.get_cloudwatch_metric('AWS/ECS', 'MemoryUtilization', 
                                                        [{'Name': 'ClusterName', 'Value': cluster_name},
                                                         {'Name': 'ServiceName', 'Value': service_name}])

                ecs_info.append({
                    'cluster': cluster_name,
                    'service': service_name,
                    'tasks_count': tasks_count,
                    'cpu_usage': cpu_metric,
                    'memory_usage': mem_metric,
                    'last_update': last_update
                })

        return ecs_info

    def get_rds_info(self):
        rds_instances = self.rds_client.describe_db_instances()['DBInstances']
        rds_info = []

        for instance in rds_instances:
            instance_id = instance['DBInstanceIdentifier']
            cpu_metric = self.get_cloudwatch_metric('AWS/RDS', 'CPUUtilization', 
                                                    [{'Name': 'DBInstanceIdentifier', 'Value': instance_id}])
            mem_metric = self.get_cloudwatch_metric('AWS/RDS', 'FreeableMemory', 
                                                    [{'Name': 'DBInstanceIdentifier', 'Value': instance_id}])
            
            rds_info.append({
                'instance_id': instance_id,
                'cpu_usage': cpu_metric,
                'free_memory': mem_metric
            })

        return rds_info

    def get_cloudwatch_metric(self, namespace, metric_name, dimensions):
        response = self.cloudwatch_client.get_metric_statistics(
            Namespace=namespace,
            MetricName=metric_name,
            Dimensions=dimensions,
            StartTime=datetime.utcnow() - timedelta(minutes=5),
            EndTime=datetime.utcnow(),
            Period=300,
            Statistics=['Average']
        )
        if response['Datapoints']:
            return response['Datapoints'][0]['Average']
        return 0