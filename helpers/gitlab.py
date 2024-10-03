from config import Config
from gitlab import Gitlab

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
            config = Config()
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