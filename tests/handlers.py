import sys

sys.path.append('../')

import database.model as db_model
from logs import logged_execution


@logged_execution
def handle_clear_db(message, bot, pool):
    db_model.truncate_tables(pool)
    bot.send_message(message.chat.id, "Done!")
