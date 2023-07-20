import json
import sys

from telebot import TeleBot
from telebot.types import Message

sys.path.append('../')

import database.model as db_model
from database.ydb_settings import pool
from logs import logger, logged_execution


@logged_execution
def handle_clear_db(message: Message, bot: TeleBot):
    db_model.truncate_tables(pool)
    bot.send_message(message.chat.id, "Done!")
