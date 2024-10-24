import boto3
from botocore.exceptions import ClientError, ProfileNotFound
from datetime import datetime, timedelta

class AWSResourceManager:

    status = "idle"

    def __init__(self, aws_access_key=None, aws_secret_key=None, aws_region=None):
        self.status = "initialized"
        if aws_access_key != None and aws_secret_key != None and aws_region != None:
            self.setup(aws_access_key, aws_secret_key, aws_region)


    def setup(self, aws_access_key, aws_secret_key, aws_region):
        try:        
            self.session = boto3.Session(
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                region_name=aws_region
            )
            self.ecs_client = self.session.client('ecs')
            self.rds_client = self.session.client('rds')
            self.cloudwatch_client = self.session.client('cloudwatch')
            self.status = "configured"
        except Exception as e:
            self.status = "error"
            raise Exception(f"Error setting up AWS resource manager: {str(e)}")

    def get_ecs_info(self):
        if self.status != "configured":
            raise Exception("AWS resource manager not configured")

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

                health_score = self.calculate_health_score(cpu_metric, mem_metric)
                
                ecs_info.append({
                    'cluster': cluster_name,
                    'service': service_name,
                    'tasks_count': tasks_count,
                    'cpu_usage': cpu_metric,
                    'memory_usage': mem_metric,
                    'last_update': last_update,
                    'health': {
                        'status': self.get_health_status(health_score),
                        'score': health_score
                    }
                })

        return ecs_info

    def get_rds_info(self):
        if self.status != "configured":
            raise Exception("AWS resource manager not configured")
        
        rds_instances = self.rds_client.describe_db_instances()['DBInstances']
        rds_info = []
        total_cpu_percent = 0
        total_mem_percent = 0
        instance_count = len(rds_instances)

        for instance in rds_instances:
            instance_id = instance['DBInstanceIdentifier']
            
            # Get CPU utilization (already in percentage)
            cpu_metric = self.get_cloudwatch_metric('AWS/RDS', 'CPUUtilization', 
                                                [{'Name': 'DBInstanceIdentifier', 'Value': instance_id}])
            
            # Get memory metrics
            free_memory = self.get_cloudwatch_metric('AWS/RDS', 'FreeableMemory', 
                                                [{'Name': 'DBInstanceIdentifier', 'Value': instance_id}])
            
            # Get total memory from instance info
            instance_class = instance['DBInstanceClass']
            total_memory = self.get_instance_memory(instance_class)  # You'll need to implement this method
            
            # Calculate memory usage percentage
            used_memory = total_memory - free_memory
            memory_usage_percent = (used_memory / total_memory) * 100 if total_memory > 0 else 0
            
            # Add to totals for averaging
            total_cpu_percent += cpu_metric
            total_mem_percent += memory_usage_percent
            
            rds_info.append({
                'instance_id': instance_id,
                'cpu_usage': round(cpu_metric, 2),
                'memory_usage': round(memory_usage_percent, 2),
            })

        # Calculate averages
        avg_cpu_percent = round(total_cpu_percent / instance_count, 2) if instance_count > 0 else 0
        avg_mem_percent = round(total_mem_percent / instance_count, 2) if instance_count > 0 else 0

        health_score = self.calculate_health_score(avg_cpu_percent, avg_mem_percent)
        
        return {
            'instance_count' : instance_count,
            'instances': rds_info,
            'status': self.get_health_status(health_score),
            'averages': {
                'health': health_score,
                'cpu': avg_cpu_percent,
                'memory': avg_mem_percent
            }
        }

    def calculate_health_score(self, cpu_percent, memory_percent):
        """
        Calcula um score de saúde combinando CPU e memória.
        Retorna um valor de 0 a 100, onde:
        - 100 é o melhor (baixo uso)
        - 0 é o pior (uso muito alto)
        """
        # Pesos para cada métrica (ajuste conforme necessidade)
        CPU_WEIGHT = 0.5
        MEMORY_WEIGHT = 0.5
        
        # Inverte a porcentagem para que menor uso = maior score
        cpu_score = 100 - cpu_percent
        memory_score = 100 - memory_percent
        
        # Calcula o score ponderado
        weighted_score = (cpu_score * CPU_WEIGHT) + (memory_score * MEMORY_WEIGHT)
        
        return round(weighted_score, 2)


    def get_health_status(self, health_score):
        """
        Converte o score numérico em um status mais amigável
        """
        if health_score >= 80:
            return {
                'level': 'Ótimo',
                'color': 'green',
                'description': 'Recursos sendo bem utilizados'
            }
        elif health_score >= 60:
            return {
                'level': 'Bom',
                'color': 'blue',
                'description': 'Uso normal dos recursos'
            }
        elif health_score >= 40:
            return {
                'level': 'Atenção',
                'color': 'yellow',
                'description': 'Recursos com uso elevado'
            }
        elif health_score >= 20:
            return {
                'level': 'Crítico',
                'color': 'orange',
                'description': 'Recursos próximos do limite'
            }
        else:
            return {
                'level': 'Emergência',
                'color': 'red',
                'description': 'Recursos sobrecarregados'
            }

    def get_instance_memory(self, instance_class):
        """
        Returns total memory in bytes for a given RDS instance class.
        You'll need to maintain this mapping based on AWS instance types.
        """
        # Memory sizes in bytes for different instance classes
        memory_map = {
            'db.t3.micro': 1 * 1024 * 1024 * 1024,  # 1 GB
            'db.t3.small': 2 * 1024 * 1024 * 1024,  # 2 GB
            'db.t3.medium': 4 * 1024 * 1024 * 1024,  # 4 GB
            'db.r5.large': 16 * 1024 * 1024 * 1024,  # 16 GB
            'db.r5.xlarge': 32 * 1024 * 1024 * 1024,  # 32 GB
            # Add more instance types as needed
        }
    
        return memory_map.get(instance_class, 0)

    def get_cloudwatch_metric(self, namespace, metric_name, dimensions):
        if self.status != "configured":
            raise Exception("AWS resource manager not configured")
        
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