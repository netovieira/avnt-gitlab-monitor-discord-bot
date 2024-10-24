import os
import importlib
from core.db.DB import DB
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('discord:setup:config')

class Config(DB):
    
    def __init__(self, db_path=None):
        super().__init__(db_path)


    async def initialize(self):
        logger.debug('Initializing config...')
        db_dir = os.path.join(os.path.dirname(__file__), 'core', 'db')
        for filename in os.listdir(db_dir):
            if filename.endswith('.py') and filename != '__init__.py':
                module_name = f'core.db.{filename[:-3]}'
                module = importlib.import_module(module_name)
                for name, obj in module.__dict__.items():
                    if isinstance(obj, type) and issubclass(obj, DB) and obj != DB:
                        instance = obj()
                        await instance.initialize()
                        logger.debug(f'{name} inicialized!')
                        
        logger.debug('Setup inicialized!')
        

        

    
