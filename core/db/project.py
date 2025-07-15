from core.db.DB import DB, DotDict
import aiosqlite


def projectFields() -> list[str]:
    return [
        'id',
        'thread_id',
        'channel_id',
        'group_id',
        'name',
        'channel_name',
        'group_name',
        'project_url'
    ]

def projectFromCursor(row): 
    return DotDict({
        'id': row[0],
        'thread_id': row[1],
        'channel_id': row[2],
        'group_id': row[3],
        'name': row[4],
        'channel_name': row[5],
        'group_name': row[6],
        'url': row[7],
    })

class Project(DB):

    async def initialize(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS projects
                (
                             id INTEGER PRIMARY KEY, 
                             thread_id TEXT,
                             channel_id TEXT,
                             group_id TEXT,
                             name TEXT,
                             channel_name TEXT,
                             group_name TEXT,
                             project_url TEXT
                )
            ''')

    ### PROJECT DATA FUNCTIONS
    async def get_projects(self):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(f'SELECT {", ".join(projectFields())} FROM projects') as cursor:
                return await cursor.fetchall()
            

    async def get_projects_by_group_id(self, group_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(f'SELECT {", ".join(projectFields())} FROM projects WHERE group_id = ?', (group_id,)) as cursor:
                rows = await cursor.fetchall()
                return [projectFromCursor(row) for row in rows if row]

    async def get_project(self, id):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(f'SELECT {", ".join(projectFields())} FROM projects WHERE id = ?', (id,)) as cursor:
                row = await cursor.fetchone()
                return row if row else None

    async def set_project(self, project_id, project_name, project_group, channel_id, group_id, project_url, thread_id=None):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('INSERT OR REPLACE INTO projects (id, name, group_name, channel_id, group_id, project_url) VALUES (?, ?, ?, ?, ?, ?)',
                             (project_id, project_name, project_group, channel_id, group_id, project_url))
            
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
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(f'SELECT {", ".join(projectFields())} FROM projects WHERE thread_id = ?', (thread_id,)) as cursor:
                row = await cursor.fetchone()
                return row if row else None