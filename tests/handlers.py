import sys
from time import sleep

from user_interaction import texts


sys.path.append('../')

import database.model as db_model
from logs import logged_execution


@logged_execution
def handle_clear_db(message, bot, pool):
    db_model.truncate_tables(pool)
    bot.send_message(message.chat.id, "Done!")


@logged_execution
def handle_stop(message, bot, pool):
    sleep(2)
    bot.delete_state(message.from_user.id, message.chat.id)
    bot.send_message(message.chat.id, texts.stop_message)
