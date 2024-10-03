import logging

def getLogger(tag='discord', level=logging.DEBUG):
    logging.basicConfig(level=level)
    l = logging.getLogger(tag)
    l.setLevel(logging.DEBUG)
    handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    l.addHandler(handler)
    return l