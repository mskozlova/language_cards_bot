import database.model as db_model
from database.ydb_settings import pool
from logs import logger, logged_execution
from user_interaction import texts

from bot import constants, keyboards, states, utils


@logged_execution
def handle_language_not_set(message, bot):
    bot.send_message(message.chat.id, texts.no_language_is_set)


@logged_execution
def suggest_group_choices(message, bot, next_state):
    language = db_model.get_current_language(pool, message.chat.id)
    if language is None:
        handle_language_not_set(message, bot)
        return
    
    groups = db_model.get_all_groups(pool, message.chat.id, language)
    group_names = sorted([group["group_name"].decode() for group in groups])
    
    if len(groups) == 0:
        bot.reply_to(message, texts.no_groups_yet)
        return
    
    bot.set_state(message.from_user.id, next_state, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["language"] = language
        data["group_names"] = group_names
    
    markup = keyboards.get_reply_keyboard(group_names, ["/exit"], row_width=3)
    
    bot.send_message(
        message.chat.id,
        texts.group_choose,
        reply_markup=markup
    )


def get_number_of_batches(batch_size, total_number):
    n_batches = total_number // batch_size
    if total_number % batch_size > 0:
        n_batches += 1
    return n_batches


def save_words_edit_to_group(chat_id, language, group_id, words, action):
    if len(words) > 0:
        if action == "add":
            db_model.add_words_to_group(pool, chat_id, language, group_id, words)
        elif action == "delete":
            db_model.delete_words_from_group(pool, chat_id, language, group_id, words)

    return len(words)
