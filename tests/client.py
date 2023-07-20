import os

from pyrogram import Client


api_id = os.environ.get("TELEGRAM_API_ID")
api_hash = os.environ.get("TELEGRAM_API_HASH")
client = Client("languagecardsbottester", api_id, api_hash)
