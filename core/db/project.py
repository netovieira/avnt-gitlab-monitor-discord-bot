from core.db.DB import DB, DotDict
import aiosqlite

def projectFromCursor(row): 
    return DotDict({
        'id': row[0],
        'name': row[1],
        'group_name': row[2],
        'repository_url': row[3],
        'channel_id': row[4],
        'group_id': row[5],
        'thread_id': row[6]
    })

class Project(DB):

    fields = ['id', 'name', 'group_name', 'repository_url', 'channel_id', 'group_id', 'thread_id']

    async def initialize(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS projects
                (
                             id INTEGER PRIMARY KEY, 
                             name TEXT, 
                             group_name TEXT, 
                             repository_url TEXT, 
                             group_id TEXT, 
                             channel_id TEXT, 
                             thread_id TEXT )
            ''')

    ### PROJECT DATA FUNCTIONS
    async def get_projects(self):
        fields = ', '.join(self.fields)

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(f'SELECT {fields} FROM projects') as cursor:
                return await cursor.fetchall()
            

    async def get_projects_by_group_id(self, group_id: int):
        fields = ', '.join(self.fields)

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(f'SELECT {fields} FROM projects WHERE group_id = ?', (group_id,)) as cursor:
                rows = await cursor.fetchall()
                return [projectFromCursor(row) for row in rows if row]

    async def get_project(self, id):
        fields = ', '.join(self.fields)

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(f'SELECT {fields} FROM projects WHERE id = ?', (id,)) as cursor:
                row = await cursor.fetchone()
                return row if row else None

    async def set_project(self, project_id, project_name, project_group, channel_id, group_id, repository_urL='', thread_id=None):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(f'INSERT OR REPLACE INTO projects (id, name, group_name, channel_id, group_id, repository_urL) VALUES (?, ?, ?, ?, ?, ?)', 
                             (project_id, project_name, project_group, channel_id, group_id, repository_urL))
            
            if thread_id is not None:
                await self.set_thread(project_id, thread_id) 
            else:
                await db.commit()

    async def remove_project(self, project_id):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('DELETE FROM projects WHERE id = ?', (project_id,))
            await db.commit()

    async def set_thread(self, project_id, thread_id):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('UPDATE projects SET thread_id = ? WHERE id = ?', (thread_id, project_id))
            await db.commit()

    async def unset_thread(self, project_id, thread_id):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('UPDATE projects SET thread_id = null WHERE id = ? and thread_id = ?', (project_id, thread_id))
            await db.commit()

    async def get_project_by_thread(self, thread_id):
        fields = ', '.join(self.fields)

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(f'SELECT {fields} FROM projects WHERE thread_id = ?', (thread_id,)) as cursor:
                row = await cursor.fetchone()
                return row if row else None