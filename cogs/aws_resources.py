from discord.ext import commands
from core.cog import Cog
from core.db.aws_project import AWSProject
from helpers.datetime import format_date
from core.aws_resource_manager import AWSResourceManager
from botocore.exceptions import ClientError, ProfileNotFound

class AWSResourcesCog(Cog):
    def __init__(self, bot):
        super().__init__(bot, loggerTag='aws_resources')

    @commands.command(name="aws_resources", description="Get AWS resource usage information")
    async def aws_resources(self, ctx, project_id: int, environment: str):
        try:

            _ = AWSProject()
            project = await _.get_aws_project(project_id, environment)

            aws_manager = AWSResourceManager(project.aws_access_key, project.aws_secret_key, project.aws_region)
            
            ecs_info = aws_manager.get_ecs_info()
            rds_info = aws_manager.get_rds_info()

            # Format the response
            response = "AWS Resources Information:\n\n"
            response += "ECS Resources:\n"
            for info in ecs_info:
                response += (f"Cluster: {info['cluster']}, Service: {info['service']}\n"
                             f"  Tasks Count: {info['tasks_count']}\n"
                             f"  CPU Usage: {info['cpu_usage']:.2f}%\n"
                             f"  Memory Usage: {info['memory_usage']:.2f}%\n"
                             f"  Last Update: {format_date(info['last_update'].strftime('%Y-%m-%d %H:%M:%SZ'))}\n\n")

            response += "RDS Resources:\n"
            for info in rds_info:
                response += (f"Instance: {info['instance_id']}\n"
                             f"  CPU Usage: {info['cpu_usage']:.2f}%\n"
                             f"  Free Memory: {info['free_memory']:.2f} MB\n\n")

            await ctx.send(response)

        except ClientError as e:
            await ctx.send(f"An error occurred while accessing AWS: {str(e)}")
        except ProfileNotFound as e:
            await ctx.send(f"AWS profile error: {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred: {str(e)}")

async def setup(bot):
    await bot.add_cog(AWSResourcesCog(bot))