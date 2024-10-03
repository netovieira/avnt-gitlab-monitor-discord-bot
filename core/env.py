import os
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
WEBHOOK_PORT = int(os.getenv('WEBHOOK_PORT', 5000))
WEBHOOK_HOST = os.getenv('WEBHOOK_HOST', 'https://192.168.1.28') 

logger.info(f'<<==============================================================================  START  ==============================================================================>>')
logger.info(f' WEBHOOK_PORT: {WEBHOOK_PORT}, WEBHOOK_HOST: {WEBHOOK_HOST}, TOKEN: {TOKEN}')
logger.info(f'<<==============================================================================   END   ==============================================================================>>')

