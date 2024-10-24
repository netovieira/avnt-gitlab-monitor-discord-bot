from core.db.DB import DB, DotDict
import aiosqlite
from typing import List, Optional

def fromCursor(row): 
    return DotDict({
        'id': row[0],
        'environment': row[1],
        'aws_access_key': row[2],
        'aws_secret_key': row[3],
        'aws_region': row[4]
    })

class AWSProject(DB):

    async def initialize(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS aws_projects
                (
                             id INTEGER,
                             environment TEXT,
                             aws_secret_key TEXT, 
                             aws_access_key TEXT, 
                             aws_region TEXT,
                             PRIMARY KEY (id, environment) )
            ''')

    ### AWS PROJECTS DATA FUNCTIONS
    async def get_aws_projects(self, environment: Optional[str] = None, project_id: Optional[int] = None) -> List[dict]:
        """
        Get AWS projects with optional filtering by environment and/or project ID.
        
        Args:
            environment: Optional environment to filter by (e.g., 'dev', 'prod')
            project_id: Optional project ID to filter by
            
        Returns:
            List of AWS project dictionaries
        """
        query = '''
            SELECT id, environment, aws_access_key, aws_secret_key, aws_region 
            FROM aws_projects
        '''
        params = []
        conditions = []

        if environment:
            conditions.append('environment = ?')
            params.append(environment)
        
        if project_id:
            conditions.append('id = ?')
            params.append(project_id)

        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [fromCursor(row) for row in rows if row]

    async def get_aws_project(self, id, environment):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT id, environment, aws_access_key, aws_secret_key, aws_region FROM aws_projects WHERE id = ? and environment = ?', (id,environment)) as cursor:
                row = await cursor.fetchone()
                return fromCursor(row) if row else None

    async def set_aws_project(self, project_id, environment, aws_access_key, aws_secret_key, aws_region):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('INSERT OR REPLACE INTO aws_projects (id, environment, aws_access_key, aws_secret_key, aws_region) VALUES (?, ?, ?, ?, ?)', 
                             (project_id, environment, aws_access_key, aws_secret_key, aws_region))
            await db.commit()

    async def remove_aws_project(self, project_id, environment):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('DELETE FROM aws_projects WHERE id = ? and environment = ?', (project_id,environment))
            await db.commit()