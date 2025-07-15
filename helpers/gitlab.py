from typing import Optional, List
from datetime import datetime
from gitlab import Gitlab
from gitlab.v4.objects import Project
from dataclasses import dataclass
from core.db.gitlab import Gitlab as GitlabConfig

@dataclass
class PipelineInfo:
    """Data class for pipeline information"""
    id: int
    status: str
    translated_status: str
    ref: str
    sha: str
    created_at: datetime
    updated_at: datetime
    web_url: str
    environment: Optional[str]

    @classmethod
    def from_pipeline(cls, pipeline, environment: Optional[str] = None) -> 'PipelineInfo':
        """Create PipelineInfo from a GitLab pipeline object"""
        return cls(
            id=pipeline.id,
            status=pipeline.status,
            translated_status=translate_pipeline_status(pipeline.status),
            ref=pipeline.ref,
            sha=pipeline.sha,
            created_at=datetime.strptime(pipeline.created_at, '%Y-%m-%dT%H:%M:%S.%fZ'),
            updated_at=datetime.strptime(pipeline.updated_at, '%Y-%m-%dT%H:%M:%S.%fZ'),
            web_url=pipeline.web_url,
            environment=environment
        )

def translate_pipeline_status(status: str) -> str:
    """Translate pipeline status to Portuguese"""
    translations = {
        'running': 'Em execução',
        'pending': 'Pendente',
        'success': 'Sucesso',
        'failed': 'Falhou',
        'canceled': 'Cancelado',
        'skipped': 'Ignorado',
        'manual': 'Manual',
        'scheduled': 'Agendado'
    }
    return translations.get(status, status)

def translate_merge_status(status: str) -> str:
    """Translate merge request status to Portuguese"""
    translations = {
        'cannot_be_merged': 'Não pode ser mesclado',
        'can_be_merged': 'Pode ser mesclado',
        'unchecked': 'Não verificado',
        'checking': 'Verificando',
        'mergeable': 'Pode ser mesclado',
        'conflict': 'Conflitante',
        'unknown': 'Desconhecido'
    }
    return translations.get(status, status)

class GitlabClient:
    def __init__(self):
        self.instance = None
        self.url = None
        self.token = None

    @classmethod
    async def create(cls, url=None, token=None):
        self = cls()
        await self.initialize(url, token)
        return self

    async def initialize(self, url=None, token=None):
        if url is None or token is None:
            config = GitlabConfig()
            if url is None:
                self.url = await config.get_gitlab_config('url')
            else:
                self.url = url
            if token is None:
                self.token = await config.get_gitlab_config('token')
            else:
                self.token = token

        if self.token is not None and self.url is not None:
            self.instance = Gitlab(self.url, private_token=self.token)
        else:
            raise Exception("GitLab configuration is not set. Please use !config_gitlab first.")

    @classmethod
    async def get_instance(cls):
        if cls.instance is None:
            cls.instance = await cls.create()
        return cls.instance

    def get_project(self, project_id: int) -> Project:
        """Get GitLab project by ID"""
        return self.instance.projects.get(project_id)

    def get_last_pipeline(self, project_id: int, environment: Optional[str] = None, ref: Optional[str] = None) -> Optional[PipelineInfo]:
        """
        Get the last pipeline for a project, optionally filtered by environment and ref.
        
        Args:
            project_id: GitLab project ID
            environment: Optional environment name to filter by
            ref: Optional branch/tag name to filter by
            
        Returns:
            PipelineInfo object containing pipeline details or None if not found
        """
        try:
            project = self.get_project(project_id)
            
            # Build pipeline filter
            pipeline_filter = {
                'order_by': 'id', 
                'sort': 'desc',
                'per_page': 1
            }
            if ref:
                pipeline_filter['ref'] = ref

            # Get pipelines
            pipelines = project.pipelines.list(**pipeline_filter)
            
            if not pipelines:
                return None

            if environment:
                # Since we're only getting one pipeline, we can simplify this part
                pipeline_detail = project.pipelines.get(pipelines[0].id)
                for job in pipeline_detail.jobs.list():
                    if hasattr(job, 'environment') and job.environment and job.environment['name'] == environment:
                        return PipelineInfo.from_pipeline(pipeline_detail, environment)
                return None
            else:
                # Return the latest pipeline regardless of environment
                pipeline_detail = project.pipelines.get(pipelines[0].id)
                return PipelineInfo.from_pipeline(pipeline_detail)

        except Exception as e:
            raise Exception(f"Failed to get pipeline information: {str(e)}")
    
    def get_environment_pipelines(self, project_id: int, environment: str, limit: int = 10) -> List[PipelineInfo]:
        """
        Get recent pipelines for a specific environment.
        
        Args:
            project_id: GitLab project ID
            environment: Environment name to filter by
            limit: Maximum number of pipelines to return
            
        Returns:
            List of PipelineInfo objects
        """
        try:
            project = self.get_project(project_id)
            pipelines = []
            
            for pipeline in project.pipelines.list(order_by='id', sort='desc'):
                if len(pipelines) >= limit:
                    break
                    
                pipeline_detail = project.pipelines.get(pipeline.id)
                for job in pipeline_detail.jobs.list():
                    if hasattr(job, 'environment') and job.environment and job.environment['name'] == environment:
                        pipelines.append(PipelineInfo.from_pipeline(pipeline_detail, environment))
                        break
                        
            return pipelines

        except Exception as e:
            raise Exception(f"Failed to get environment pipelines: {str(e)}")
        

    def get_default_branch(self, project_id: int) -> Optional[str]:
        """
        Get the default branch name (main or master) for a GitLab project.

        Args:
            project_id: GitLab project ID
                
        Returns:
            str: Name of the default branch (e.g., 'main' or 'master')
            None: If project not found or error occurs
        """
        try:
            project = self.get_project(project_id)
            return project.default_branch
            
        except Exception as e:
            raise Exception(f"Failed to get default branch: {str(e)}")



def get_project_url(project_id: int) -> str:
    """Get GitLab project URL from project ID"""
    return f"https://gitlab.com/{project_id}"