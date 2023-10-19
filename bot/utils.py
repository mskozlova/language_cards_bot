import re

import emojis

import database.model as db_model
from bot import keyboards
from logs import logged_execution
from user_interaction import texts


@logged_execution
def handle_language_not_set(message, bot):
    bot.send_message(message.chat.id, texts.no_language_is_set)


@logged_execution
def suggest_group_choices(message, bot, pool, next_state):
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

    return bot.send_message(message.chat.id, texts.group_choose, reply_markup=markup)


@logged_execution
def get_number_of_batches(batch_size, total_number):
    n_batches = total_number // batch_size
    if total_number % batch_size > 0:
        n_batches += 1
    return n_batches


@logged_execution
def check_language_name(name):
    return (  # emoji
        len(emojis.get(name)) == 1
        and emojis.db.get_emoji_by_alias(emojis.decode(name)[1:-1]) is not None
        and emojis.db.get_emoji_by_alias(emojis.decode(name)[1:-1]).category == "Flags"
    ) or re.fullmatch(  # text
        "[a-z]+", name
    ) is not None


@logged_execution
def check_group_name(name):
    return re.fullmatch("[0-9a-z_]+", name) is not None


@logged_execution
def save_words_edit_to_group(pool, chat_id, language, group_id, words, action):
    if len(words) > 0:
        if action == "add":
            db_model.add_words_to_group(pool, chat_id, language, group_id, words)
        elif action == "delete":
            db_model.delete_words_from_group(pool, chat_id, language, group_id, words)

    return len(words)


@logged_execution
def clear_history(bot, chat_id, from_message_id, to_message_id):
    for message_id in range(from_message_id, to_message_id):
        bot.delete_message(chat_id, message_id)
