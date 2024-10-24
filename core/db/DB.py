class DotDict:
    def __init__(self, dictionary):
        for key, value in dictionary.items():
            setattr(self, key, value)


class DB:
    def __init__(self, db_path='gino.db'):
        self.db_path = db_path

        
