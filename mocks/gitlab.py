import random
import datetime

class GitLabMock:
    def __init__(self):
        self.projects = [
            "Frontend App",
            "Backend API",
            "Mobile App",
            "Data Analytics",
            "DevOps Tools"
        ]
        self.authors = [
            "Alice Johnson",
            "Bob Smith",
            "Charlie Brown",
            "Diana Ross",
            "Ethan Hunt"
        ]
        self.pipeline_statuses = ["success", "failed", "running"]
        self.commit_messages = [
            "Fix critical bug in login flow",
            "Add new feature: user notifications",
            "Refactor database queries for performance",
            "Update dependencies to latest versions",
            "Implement CI/CD pipeline improvements"
        ]

    def get_project_data(self, project_name):
        return {
            "name": project_name,
            "pipeline_status": random.choice(self.pipeline_statuses),
            "last_update": datetime.datetime.now() - datetime.timedelta(minutes=random.randint(5, 60)),
            "last_commit_author": random.choice(self.authors),
            "last_commit_message": random.choice(self.commit_messages),
            "last_pipeline_run": datetime.datetime.now() - datetime.timedelta(hours=random.randint(1, 24)),
            "gitlab_url": f"https://gitlab.com/mock-org/{project_name.lower().replace(' ', '-')}",
            "open_issues": random.randint(0, 20),
            "open_merge_requests": random.randint(0, 10),
            "code_coverage": random.randint(70, 100)
        }

gitlab_mock = GitLabMock()