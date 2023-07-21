from logs import logged_execution
from user_interaction import texts


@logged_execution
def handle_language_not_set(message, bot):
    bot.send_message(message.chat.id, texts.no_language_is_set)
