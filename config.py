import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
CONTACT = os.getenv("CONTACT")
ADDRESS = os.getenv("ADDRESS")
WEBAPP_URL = os.getenv("WEBAPP_URL")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")
if not OWNER_ID:
    raise RuntimeError("OWNER_ID not set")
if not CONTACT:
    raise RuntimeError("CONTACT not set")
if not ADDRESS:
    raise RuntimeError("ADDRESS not set")
