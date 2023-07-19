from hashlib import blake2b
import json
import os
import random
import re

import telebot
from telebot import custom_filters
from telebot import types

import bot.states as bot_states
import bot.handlers as handlers
import database.model as db_model
from database.ydb_settings import pool
from logs import logger, logged_execution, CallbackLogger
import user_interaction.config as config
import user_interaction.options as options
import user_interaction.texts as texts
from word import compare_user_input_with_db, get_translation, get_word, get_overall_score, get_total_trains, format_word_for_listing
from word import format_word_for_group_action, get_word_from_group_action


state_storage = bot_states.StateYDBStorage(pool)
bot = telebot.TeleBot(os.environ.get("BOT_TOKEN"), state_storage=state_storage)
empty_markup = types.ReplyKeyboardRemove()


###################
# Command handlers
###################


bot.register_message_handler(handlers.handle_help, commands=["help", "start"], pass_bot=True)

bot.register_message_handler(handlers.handle_forget_me, commands=["forget_me"], pass_bot=True)
bot.register_message_handler(handlers.process_forget_me, state=bot_states.ForgetMeState.init, pass_bot=True)

bot.register_message_handler(handlers.handle_set_language, commands=["set_language"], pass_bot=True)
bot.register_message_handler(handlers.process_setting_language_cancel, commands=["cancel"],
                             state=bot_states.SetLanguageState.init, pass_bot=True)
bot.register_message_handler(handlers.process_setting_language,
                             state=bot_states.SetLanguageState.init, pass_bot=True)

bot.register_message_handler(handlers.handle_add_words, commands=["add_words"], pass_bot=True)
bot.register_message_handler(handlers.process_adding_words, state=bot_states.AddWordsState.add_words, pass_bot=True)
bot.register_message_handler(handlers.process_word_translation_stop, commands=["stop"],
                             state=bot_states.AddWordsState.translate, pass_bot=True)
bot.register_message_handler(handlers.process_word_translation,
                             state=bot_states.AddWordsState.translate, pass_bot=True)

def handle_language_not_set(message, bot):
    bot.send_message(message.chat.id, texts.no_language_is_set)


# TODO: delete all unnecessary messages
@bot.message_handler(commands=["show_words"])
@logged_execution
def handle_show_words(message):
    language = db_model.get_current_language(pool, message.chat.id)
    if language is None:
        handle_language_not_set(message)
        return

    vocab = db_model.get_full_vocab(pool, message.chat.id, language)
    for word in vocab:
        word["score"] = get_overall_score(word)
        word["n_trains"] = get_total_trains(word)
    
    # TODO: make all keyboards one time
    markup = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True, one_time_keyboard=True)
    markup.add(*options.show_words_sort_options, row_width=2)
    markup.add(telebot.types.KeyboardButton("/exit"))
    
    reply_message = bot.send_message(message.chat.id, texts.choose_sorting, reply_markup=markup)
    bot.register_next_step_handler(
        reply_message, CallbackLogger(process_choose_word_sort),
        words=vocab, original_command="/show_words"
    )


def process_choose_word_sort(message, words, original_command):
    if message.text == "/exit":
        bot.reply_to(message, texts.exited, reply_markup=empty_markup)
        return
    if message.text not in options.show_words_sort_options:
        bot.reply_to(message, texts.sorting_not_supported.format(original_command), reply_markup=empty_markup)
        return
    
    # TODO: get rid of string constants
    if message.text == "a-z":
        words = sorted(words, key=lambda w: w["word"])
    elif message.text == "z-a":
        words = sorted(words, key=lambda w: w["word"])[::-1]
    elif message.text == "n trains ⬇️":
        words = sorted(words, key=lambda w: w["n_trains"])[::-1]
    elif message.text == "n trains ⬆️":
        words = sorted(words, key=lambda w: w["n_trains"])
    elif message.text == "time added ⬇️":
        words = sorted(words, key=lambda w: w["added_timestamp"])[::-1]
    elif message.text == "time added ⬆️":
        words = sorted(words, key=lambda w: w["added_timestamp"])
    elif message.text == "score ⬇️":
        unknown_score = list(filter(lambda w: w["score"] is None, words))
        known_score = list(filter(lambda w: w["score"] is not None, words))
        words = sorted(known_score, key=lambda w: w["score"])[::-1]
        words.extend(unknown_score)
    elif message.text == "score ⬆️":
        unknown_score = list(filter(lambda w: w["score"] is None, words))
        known_score = list(filter(lambda w: w["score"] is not None, words))
        words = sorted(known_score, key=lambda w: w["score"])
        words.extend(unknown_score)
    
    CallbackLogger(process_show_words_batch)(
        message, words=words,
        batch_size=20, batch_number=0,
        original_command="/show_words"
    )


def process_show_words_batch(message, words, batch_size, batch_number, original_command):
    if batch_number != 0:
        if message.text == "/exit":
            bot.send_message(message.chat.id, texts.exited, reply_markup=empty_markup)
            return
        if message.text != "/next":
            bot.send_message(message.chat.id, texts.unknown_command.format(original_command),
                            reply_markup=empty_markup)
            return
    
    words_batch = words[batch_number * batch_size:(batch_number + 1) * batch_size]
    words_formatted = [format_word_for_listing(word) for word in words_batch]
    
    if len(words_batch) == 0:
        bot.send_message(message.chat.id, texts.no_more_words, reply_markup=empty_markup)
        return
    
    n_pages = len(words) // batch_size
    if len(words) % batch_size > 0:
        n_pages += 1
        
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=True)
    markup.add(*["/exit", "/next"], row_width=2)
    
    bot.send_message(
        message.chat.id,
        texts.word_formatted.format(batch_number + 1, n_pages, "\n".join(words_formatted)),
        reply_markup=markup, parse_mode="MarkdownV2"
    )
    
    bot.register_next_step_handler(
        message, CallbackLogger(process_show_words_batch),
        words=words, batch_size=batch_size, batch_number=batch_number+1, original_command=original_command
    )


@bot.message_handler(commands=["show_current_language"])
@logged_execution
def handle_show_current_languages(message):
    current_language = db_model.get_current_language(pool, message.chat.id)
    if current_language is not None:
        bot.reply_to(
            message,
            texts.current_language.format(current_language)
        )
    else:
        handle_language_not_set(message)


@bot.message_handler(commands=["delete_language"])
@logged_execution
def handle_delete_language(message):
    language = db_model.get_current_language(pool, message.chat.id)
    if language is None:
        handle_language_not_set(message)
        return
    
    markup = types.ReplyKeyboardMarkup(
        row_width=len(options.delete_are_you_sure),
        resize_keyboard=True, one_time_keyboard=True
    )
    markup.add(*options.delete_are_you_sure.keys(), row_width=len(options.delete_are_you_sure))
    bot.send_message(
        message.chat.id,
        texts.delete_language_warning.format(language),
        reply_markup=markup
    )
    bot.register_next_step_handler(message, CallbackLogger(process_delete_language), language=language)


def process_delete_language(message, language):
    db_model.delete_language(pool, message.chat.id, language)
    bot.send_message(message.chat.id, texts.delete_language_final.format(language))


# TODO: delete words from groups too
@bot.message_handler(commands=["delete_words"])
@logged_execution
def handle_delete_words(message):
    language = db_model.get_current_language(pool, message.chat.id)
    if language is None:
        handle_language_not_set(message)
        return

    reply_message = bot.reply_to(message, texts.delete_words_start)
    bot.register_next_step_handler(reply_message, CallbackLogger(process_deleting_words), language=language)


def process_deleting_words(message, language):
    words = message.text.split("\n")
    existing_words = db_model.get_words_from_vocab(pool, message.chat.id, language, words)
    db_model.delete_words_from_vocab(pool, message.chat.id, language, words)
    bot.reply_to(
        message,
        texts.deleted_words_list.format(
            len(existing_words),
            "\n".join([entry["word"] for entry in existing_words]),
            "" if len(existing_words) == len(words) else texts.deleted_words_unknown
        )
    )


@bot.message_handler(commands=["create_group"])
@logged_execution
def handle_create_group(message):
    current_language = db_model.get_current_language(pool, message.chat.id)
    if current_language is None:
        handle_language_not_set(message)
        return

    reply_message = bot.reply_to(message, texts.create_group_name)
    bot.register_next_step_handler(reply_message, CallbackLogger(process_group_creation), language=current_language)
        

def process_group_creation(message, language):
    # TODO: check latin letters and underscores
    # TODO: check name collisions with shared groups
    group_name = message.text.strip()
    if len(db_model.get_group_by_name(pool, message.chat.id, language, group_name)) > 0:
        bot.reply_to(message, texts.group_already_exists)
        return
    
    group_id = blake2b(digest_size=10)
    group_key = "{}-{}-{}".format(message.chat.id, language, group_name)
    group_id.update(group_key.encode())
    
    db_model.add_group(pool, message.chat.id, language=language,
                       group_name=group_name, group_id=group_id.hexdigest(), is_creator=True)
    bot.reply_to(message, texts.group_created)


def process_show_groups(message, language):
    # TODO: handle large number of groups
    groups = db_model.get_all_groups(pool, message.chat.id, language)
    
    if len(groups) == 0:
        bot.reply_to(message, texts.no_groups_yet)
        return
    
    markup = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
    markup.add(*sorted([group["group_name"].decode() for group in groups]), row_width=3)
    markup.add(telebot.types.KeyboardButton("/exit"))
    
    reply_message = bot.send_message(
        message.chat.id,
        texts.group_choose,
        reply_markup=markup
    )
    return reply_message


@bot.message_handler(commands=["delete_group"])
@logged_execution
def handle_delete_group(message):
    current_language = db_model.get_current_language(pool, message.chat.id)
    if current_language is None:
        handle_language_not_set(message)
        return

    reply_message = CallbackLogger(process_show_groups)(message, current_language)
    bot.register_next_step_handler(
        reply_message,
        CallbackLogger(process_group_deletion_check_sure),
        language=current_language
    )


def process_group_deletion_check_sure(message, language):
    if message.text == "/exit":
        bot.reply_to(message, texts.exited, reply_markup=empty_markup)
        return
    
    groups = db_model.get_group_by_name(pool, message.chat.id, language, message.text)
    
    if len(groups) == 0:
        bot.reply_to(message, texts.no_such_group.format("/delete_group"),
                     reply_markup=empty_markup)
        return
    
    if not groups[0]["is_creator"]:
        bot.reply_to(message, texts.group_not_a_creator,
                        reply_markup=empty_markup)
        return
    
    group_id = groups[0]["group_id"].decode("utf-8")
    group_name = groups[0]["group_name"].decode("utf-8")
    
    markup = types.ReplyKeyboardMarkup(
        row_width=len(options.delete_are_you_sure),
        resize_keyboard=True, one_time_keyboard=True
    )
    markup.add(*options.delete_are_you_sure.keys(), row_width=len(options.delete_are_you_sure))
    bot.send_message(
        message.chat.id,
        texts.delete_group_warning.format(group_name, language),
        reply_markup=markup
    )
    # TODO: maybe delete words, too?
    bot.register_next_step_handler(
        message, CallbackLogger(process_group_deletion),
        language=language, group_id=group_id,
        group_name=group_name, is_creator=groups[0]["is_creator"]
    )


def process_group_deletion(message, language, group_id, group_name, is_creator):
    # TODO: when sharing think of local / global deletions (use is_creator)
    if message.text not in options.delete_are_you_sure:
        bot.reply_to(message, texts.unknown_command.format("/delete_group"),
                    reply_markup=empty_markup)
        return
    
    if not options.delete_are_you_sure[message.text]:
        bot.send_message(
            message.chat.id, texts.delete_group_cancel,
            reply_markup=empty_markup
        )
        return
    
    db_model.delete_group(pool, group_id)
    bot.send_message(message.chat.id, texts.delete_group_success.format(group_name))


@bot.message_handler(commands=["show_groups"])
@logged_execution
def handle_show_groups(message):
    current_language = db_model.get_current_language(pool, message.chat.id)
    reply_message = CallbackLogger(process_show_groups)(message, current_language)
    bot.register_next_step_handler(reply_message, CallbackLogger(process_show_group), language=current_language)
    

def process_show_group(message, language):
    if message.text == "/exit":
        bot.reply_to(message, texts.show_group_done, reply_markup=empty_markup)
        return
    
    groups = db_model.get_group_by_name(pool, message.chat.id, language, message.text)
    
    if len(groups) == 0:
        bot.reply_to(message, texts.no_such_group.format("/show_groups"),
                        reply_markup=empty_markup)
        return
    
    group_id = groups[0]["group_id"].decode("utf-8")
    group_contents = sorted(db_model.get_group_contents(pool, group_id), key=lambda w: w["word"])
    for word in group_contents:
        word["score"] = get_overall_score(word)
        word["n_trains"] = get_total_trains(word)
    
    if len(group_contents) == 0:
        bot.reply_to(message, texts.show_group_empty, reply_markup=empty_markup)
        return
    
    CallbackLogger(process_show_words_batch)(
        message, group_contents,
        batch_size=20, batch_number=0,
        original_command="/show_groups"
    )
    

@bot.message_handler(commands=["group_add_words"])
@logged_execution
def handle_group_add_words(message):
    current_language = db_model.get_current_language(pool, message.chat.id)
    reply_message = CallbackLogger(process_show_groups)(message, current_language)
    bot.register_next_step_handler(
        reply_message,
        CallbackLogger(process_choose_group_to_add_words),
        language=current_language
    )


def get_keyboard_markup(choices, mask, additional_commands=[], row_width=2):
    markup = types.ReplyKeyboardMarkup(row_width=row_width, resize_keyboard=True)
        
    formatted_choices = [
        "{}{}".format(
            options.group_add_words_prefixes[mask],
            format_word_for_group_action(entry),
        ) for entry, mask in zip(choices, mask)
    ]
    if len(formatted_choices) % row_width != 0:
        formatted_choices.extend([""] * (row_width - len(formatted_choices) % row_width)) 
    
    markup.add(*formatted_choices, row_width=row_width)
    markup.add(*additional_commands, row_width=len(additional_commands))
    return markup


def save_words_edit_to_group(chat_id, language, group_id, words, action):
    if len(words) > 0:
        if action == "add":
            db_model.add_words_to_group(pool, chat_id, language, group_id, words)
        elif action == "delete":
            db_model.delete_words_from_group(pool, chat_id, language, group_id, words)

    return len(words)


def process_words_batch(message, language, group_id, group_name, all_words, current_words,
                        batch_num, batch_size, ok_message=None, chosen_words=set(), is_start=False, action="add"):
    n_batches = len(all_words) // batch_size
    if len(all_words) % batch_size > 0:
        n_batches += 1
    
    if ok_message is not None:
        bot.delete_message(ok_message.chat.id, ok_message.id)
    
    batch = all_words[batch_num * batch_size:(batch_num + 1) * batch_size]
    
    if is_start: # new page 
        current_words = {
            entry["word"]: 0 if action == "add" else 1 for entry in batch
        }
        markup = get_keyboard_markup(
            batch,
            current_words.values(),
            ["/cancel", "/exit", "/next"]
        )
        message = bot.send_message(
            message.chat.id,
            texts.group_edit_choose.format(
                action,
                group_name,
                batch_num + 1,
                n_batches
            ),
            reply_markup=markup
        )
        bot.register_next_step_handler(
            message, CallbackLogger(process_words_batch),
            language=language, group_id=group_id, group_name=group_name,
            all_words=all_words, current_words=current_words, chosen_words=chosen_words,
            batch_num=batch_num, batch_size=batch_size, action=action
        )
    elif message.text == "/exit":
        for word, mask in current_words.items():
            if action == "add" and mask == 1:
                chosen_words.add(word)
            if action == "delete" and mask == 0:
                chosen_words.add(word)
        n_edited_words = save_words_edit_to_group(message.chat.id, language, group_id, chosen_words, action)
        bot.reply_to(
            message,
            texts.group_edit_finished.format(group_name, action, n_edited_words, "\n".join(sorted(list(chosen_words)))),
            reply_markup=empty_markup
        )
        return
    elif message.text == "/cancel":
        bot.reply_to(message, texts.group_edit_cancelled, reply_markup=empty_markup)
        return
    elif message.text == "/next":
        batch_num += 1
        
        for word, mask in current_words.items():
            if action == "add" and mask == 1:
                chosen_words.add(word)
            if action == "delete" and mask == 0:
                chosen_words.add(word)

        if batch_num * batch_size >= len(all_words):
            n_edited_words = save_words_edit_to_group(message.chat.id, language, group_id, chosen_words, action)
            bot.reply_to(
                message,
                texts.group_edit_no_more_words.format(
                    group_name,
                    action,
                    n_edited_words,
                    "\n".join(sorted(list(chosen_words)))
                ),
                reply_markup=empty_markup
            )
            return
        
        CallbackLogger(process_words_batch)(
            message, language=language,
            group_id=group_id, group_name=group_name,
            all_words=all_words, current_words=None,
            batch_num=batch_num, batch_size=batch_size,
            chosen_words=chosen_words, is_start=True,
            action=action
        )

    elif get_word_from_group_action(message.text[1:]) in current_words:
        word = get_word_from_group_action(message.text[1:])
        current_words[word] = (current_words[word] + 1) % 2
        markup = get_keyboard_markup(
            batch,
            current_words.values(),
            ["/cancel", "/exit", "/next"]
        )
        ok_message = bot.send_message(message.chat.id, "Ok!", reply_markup=markup)
        bot.register_next_step_handler(
            message, CallbackLogger(process_words_batch),
            language=language, group_id=group_id, group_name=group_name,
            all_words=all_words, current_words=current_words,
            batch_num=batch_num, batch_size=batch_size, ok_message=ok_message,
            chosen_words=chosen_words,
            action=action
        )
        bot.delete_message(message.chat.id, message.id)
    else:
        bot.reply_to(message, texts.group_edit_unknown_word)
        bot.register_next_step_handler(message, CallbackLogger(process_words_batch),
                                    language=language, group_id=group_id, group_name=group_name,
                                    all_words=all_words, current_words=current_words, chosen_words=chosen_words,
                                    batch_num=batch_num, batch_size=batch_size, action=action)


def process_choose_group_to_add_words(message, language):
    if message.text == "/exit":
        bot.reply_to(message, texts.exited, reply_markup=empty_markup)
        return
    
    groups = db_model.get_group_by_name(pool, message.chat.id, language, message.text)
    
    if len(groups) == 0:
        bot.reply_to(message, texts.no_such_group.format("/group_add_words"),
                        reply_markup=empty_markup)
        return
    
    if not groups[0]["is_creator"]:
        bot.reply_to(message, texts.group_not_a_creator,
                        reply_markup=empty_markup)
        return
    
    group_id = groups[0]["group_id"].decode("utf-8")
    group_name = groups[0]["group_name"].decode("utf-8")
    
    vocabulary = db_model.get_full_vocab(pool, message.chat.id, language)
    words_in_group = set([entry["word"] for entry in db_model.get_group_contents(pool, group_id)])
    
    words_to_add = []
    for entry in vocabulary:
        if entry["word"] in words_in_group:
            continue
        words_to_add.append(entry)

    
    if len(words_to_add) == 0:
        bot.reply_to(message, texts.group_edit_full)
        return
    
    markup = types.ReplyKeyboardMarkup(row_width=4, one_time_keyboard=True, resize_keyboard=True)
    markup.add(*options.group_add_words_sort_options, row_width=4)
    markup.add(telebot.types.KeyboardButton("/exit"))
    
    reply_message = bot.send_message(message.chat.id, texts.choose_sorting, reply_markup=markup)
    bot.register_next_step_handler(
        reply_message, CallbackLogger(process_choose_sorting_to_add_words),
        language=language, group_id=group_id,
        group_name=group_name, vocabulary=words_to_add
    )
        

def process_choose_sorting_to_add_words(message, language, group_id, group_name, vocabulary):
    if message.text == "/exit":
        bot.reply_to(message, texts.exited, reply_markup=empty_markup)
        return
    
    if message.text not in options.group_add_words_sort_options:
        bot.reply_to(message, texts.sorting_not_supported.format("/group_add_words"), reply_markup=empty_markup)
        return
    
    if message.text == "a-z":
        vocabulary = sorted(vocabulary, key=lambda x: x["translation"])
    elif message.text == "time added ⬇️":
        vocabulary = sorted(vocabulary, key=lambda x: x["added_timestamp"])[::-1]

    CallbackLogger(process_words_batch)(
        message, language=language, group_id=group_id, group_name=group_name,
        all_words=vocabulary, current_words=None, chosen_words=set(),
        batch_num=0, batch_size=10, is_start=True
    )


@bot.message_handler(commands=["group_delete_words"])
@logged_execution
def handle_group_delete_words(message):
    current_language = db_model.get_current_language(pool, message.chat.id)
    reply_message = CallbackLogger(process_show_groups)(message, current_language)
    bot.register_next_step_handler(
        reply_message,
        CallbackLogger(process_choose_group_to_delete_words),
        language=current_language
    )


def process_choose_group_to_delete_words(message, language):
    if message.text == "/exit":
        bot.reply_to(message, texts.exited, reply_markup=empty_markup)
        return
    
    groups = db_model.get_group_by_name(pool, message.chat.id, language, message.text)
    
    if len(groups) == 0:
        bot.reply_to(message, texts.no_such_group.format("/group_delete_words"),
                        reply_markup=empty_markup)
        return
    
    if not groups[0]["is_creator"]:
        bot.reply_to(message, texts.group_not_a_creator,
                        reply_markup=empty_markup)
        return
    
    group_id = groups[0]["group_id"].decode("utf-8")
    group_name = groups[0]["group_name"].decode("utf-8")
    
    words_in_group = sorted(
        db_model.get_group_contents(pool, group_id),
        key=lambda entry: entry["translation"]
    )
    
    if len(words_in_group) == 0:
        bot.reply_to(message, texts.group_edit_empty)
        return

    CallbackLogger(process_words_batch)(
        message, language=language, group_id=group_id, group_name=group_name,
        all_words=words_in_group, current_words=dict(), chosen_words=set(),
        batch_num=0, batch_size=10, is_start=True, action="delete"
    )


@bot.message_handler(commands=["train"])
@logged_execution
def handle_train(message):
    current_language = db_model.get_current_language(pool, message.chat.id)
    if current_language is None:
        handle_language_not_set(message)
        return

    markup = types.ReplyKeyboardMarkup(row_width=4, one_time_keyboard=True, resize_keyboard=True)
    markup.add(*options.train_strategy_options, row_width=4)
    markup.add(telebot.types.KeyboardButton("/cancel"))
    reply_message = bot.send_message(
        message.chat.id,
        texts.training_init,
        reply_markup=markup
    )
    session_info = {"language": current_language}
    messages = [reply_message]
    bot.register_next_step_handler(
        reply_message, CallbackLogger(process_choose_strategy),
        session_info=session_info, messages=messages
    )


def init_direction_choice(message, session_info, messages):
    markup = types.ReplyKeyboardMarkup(
        row_width=len(options.train_direction_options),
        one_time_keyboard=True, resize_keyboard=True
    )
    markup.add(
        *list(options.train_direction_options.keys()),
        row_width=len(options.train_direction_options)
    )
    markup.add(telebot.types.KeyboardButton("/cancel"))
    reply_message = bot.send_message(
        message.chat.id,
        texts.training_direction,
        reply_markup=markup
    )
    messages.extend([reply_message])
    bot.register_next_step_handler(
        reply_message, CallbackLogger(process_choose_direction),
        session_info=session_info, messages=messages
    )
    

def process_choose_group_for_training(message, session_info, messages):
    if message.text == "/exit":
        bot.reply_to(message, texts.training_cancelled, reply_markup=empty_markup)
        return
        
    groups = db_model.get_group_by_name(
        pool, message.chat.id,
        session_info["language"], message.text
    )
    if len(groups) == 0:
        bot.reply_to(message, texts.no_such_group.format("/train"),
                     reply_markup=empty_markup)
        return
    
    group_id = groups[0]["group_id"].decode("utf-8")
    session_info["group_name"] = message.text
    session_info["group_id"] = group_id
    messages.append(message)
    
    init_direction_choice(message, session_info, messages)


def process_choose_strategy(message, session_info, messages):
    if message.text == "/cancel":
        bot.reply_to(message, texts.training_cancelled, reply_markup=empty_markup)
        return
    if message.text not in options.train_strategy_options:
        bot.reply_to(message, texts.training_strategy_unknown, reply_markup=empty_markup)
        return
    session_info["strategy"] = message.text
    messages.extend([message])
    
    if message.text == "group":
        reply_message = CallbackLogger(process_show_groups)(message, session_info["language"])
        messages.extend([reply_message])
        bot.register_next_step_handler(
            reply_message, CallbackLogger(process_choose_group_for_training),
            session_info=session_info, messages=messages
        )
    else:
        init_direction_choice(message, session_info, messages)


def process_choose_direction(message, session_info, messages):
    if message.text == "/cancel":
        bot.reply_to(message, texts.training_cancelled, reply_markup=empty_markup)
        return
    if message.text not in options.train_direction_options.keys():
        bot.reply_to(message, texts.training_direction_unknown, reply_markup=empty_markup)
        return

    markup = types.ReplyKeyboardMarkup(
        row_width=len(options.train_duration_options),
        one_time_keyboard=True, resize_keyboard=True
    )
    markup.add(
        *options.train_duration_options,
        row_width=len(options.train_duration_options)
    )
    markup.add(telebot.types.KeyboardButton("/cancel"))
    reply_message = bot.send_message(
        message.chat.id,
        texts.training_duration,
        reply_markup=markup
    )
    session_info["direction"] = options.train_direction_options[message.text]
    messages.extend([message, reply_message])
    bot.register_next_step_handler(
        reply_message, CallbackLogger(process_choose_duration),
        session_info, messages=messages
    )


def process_choose_duration(message, session_info, messages):
    if message.text == "/cancel":
        bot.reply_to(message, texts.training_cancelled, reply_markup=empty_markup)
        return
    if not message.text.isdigit() and message.text not in options.train_duration_options:
        bot.reply_to(message, texts.training_duration_unknown, reply_markup=empty_markup)
        return

    markup = types.ReplyKeyboardMarkup(
        row_width=len(options.train_hints_options),
        one_time_keyboard=True, resize_keyboard=True
    )
    markup.add(*options.train_hints_options, row_width=len(options.train_hints_options))
    markup.add(telebot.types.KeyboardButton("/cancel"))
    reply_message = bot.send_message(
        message.chat.id,
        texts.training_hints,
        reply_markup=markup
    )
    session_info["duration"] = int(message.text) if message.text.isdigit() else config.TRAIN_MAX_N_WORDS
    messages.extend([message, reply_message])
    bot.register_next_step_handler(
        reply_message, CallbackLogger(process_choose_hints),
        session_info, messages=messages
    )


def get_az_hint(word):
    # TODO: mask only one of possible translations
    if len(word) <= 4:
        return "*" * len(word)
    return word[0] + "*" * (len(word) - 2) + word[-1]


def format_train_message(word, translation, hints_type):
    if hints_type == "flashcards":
        return "{}\n\n||{}||".format(
            re.escape(word),
            re.escape(translation) + " " * max(40 - len(translation), 0) + "ㅤ" # invisible symbol to extend spoiler
        )
    
    if hints_type == "a****z":
        return "{}\n{}".format(
            re.escape(word),
            re.escape(get_az_hint(translation))
        )

    return "{}".format(re.escape(word))


def format_train_buttons(translation, hints, hints_type):
    if hints_type == "flashcards":
        markup = types.ReplyKeyboardMarkup(
            row_width=1,
            one_time_keyboard=True,
            resize_keyboard=True
        )
        markup.add(*["/next", "/stop"])
        return markup
    
    if hints_type != "test":
        return empty_markup
    
    all_words_list = hints + [translation, ]
    random.shuffle(all_words_list)
    markup = types.ReplyKeyboardMarkup(
        row_width=2,
        one_time_keyboard=True,
        resize_keyboard=True
    )
    markup.add(*[telebot.types.KeyboardButton(w.split("/")[0]) for w in all_words_list])
    return markup


def sample_hints(current_word, words, max_hints_number=3):
    other_words = list(filter(lambda w: w["word"] != current_word["word"], words))
    hints = random.sample(other_words, k=min(len(other_words), max_hints_number))
    return hints


def get_train_step(message, words, session_info, step, scores):
    if message.text == "/stop":
        bot.send_message(
            message.chat.id,
            texts.training_stopped,
            reply_markup=empty_markup
        )
        return
    if step != 0: # not a first iteration
        word = words[step - 1]
        is_correct = compare_user_input_with_db(
            message.text,
            word,
            session_info["hints"],
            session_info["direction"]
        )
        scores.append(int(is_correct))
        if is_correct:
            bot.send_message(
                message.chat.id,
                texts.train_correct_answer,
                reply_markup=empty_markup
            )
        else:
            bot.send_message(
                message.chat.id,
                texts.train_wrong_answer.format(
                    get_translation(word, session_info["direction"])
                ),
                reply_markup=empty_markup
            )

    if step == len(words): # training complete
        # TODO: different messages for different results
        if session_info["hints"] == "no hints":
            db_model.set_training_scores(
                pool, message.chat.id, session_info["session_id"],
                list(range(1, len(words) + 1)), scores
            )
            db_model.update_final_scores(pool, message.chat.id, session_info)
        else:
            bot.send_message(
                message.chat.id, texts.training_no_scores
            )
        bot.send_message(
            message.chat.id,
            texts.training_results.format(sum(scores), len(words)),
            reply_markup=empty_markup
        )
        return
    
    next_word = words[step]
    hints = sample_hints(next_word, words, 3)
    reply_message = bot.send_message(
        message.chat.id,
        format_train_message(
            get_word(next_word, session_info["direction"]),
            get_translation(next_word, session_info["direction"]),
            session_info["hints"]
        ),
        reply_markup=format_train_buttons(
            get_translation(next_word, session_info["direction"]),
            [get_translation(hint, session_info["direction"]) for hint in hints],
            session_info["hints"]
        ),
        parse_mode="MarkdownV2"
    )
    bot.register_next_step_handler(
        reply_message, CallbackLogger(get_train_step),
        words=words, session_info=session_info, step=step+1, scores=scores
    )


def process_choose_hints(message, session_info, messages):
    if message.text == "/cancel":
        bot.reply_to(message, texts.training_cancelled, reply_markup=empty_markup)
        return
    if message.text not in options.train_hints_options:
        bot.reply_to(message, texts.training_hints_unknown,
                    reply_markup=empty_markup)
        return
    
    session_info["hints"] = message.text
    session_info["session_id"] = db_model.get_current_time()
    messages.append(message)
    
    db_model.init_training_session(pool, message.chat.id, session_info)
    if session_info["strategy"] != "group":
        db_model.create_training_session(pool, message.chat.id, session_info)
    else:
        db_model.create_group_training_session(pool, message.chat.id, session_info)
    
    words = db_model.get_training_words(pool, message.chat.id, session_info)
    
    if len(words) == 0:
        bot.send_message(
            message.chat.id,
            texts.training_no_words_found,
            reply_markup=empty_markup
        )
        return
    
    bot.send_message(
        message.chat.id,
        texts.training_start.format(
            session_info["strategy"], len(words),
            session_info["direction"], session_info["hints"],
            texts.training_start_group.format(session_info["group_name"]) if "group_name" in session_info else ""
        ),
        reply_markup=empty_markup
    )
    if len(words) < session_info["duration"] and session_info["duration"] != config.TRAIN_MAX_N_WORDS:
        bot.send_message(
            message.chat.id,
            texts.training_fewer_words,
            reply_markup=empty_markup
        )
    # delete all technical messages if training init is successful
    for m in messages:
        bot.delete_message(message.chat.id, m.id)
    get_train_step(message=message, words=words, session_info=session_info, step=0, scores=[])


bot.register_message_handler(handlers.handle_unknown, pass_bot=True)

bot.add_custom_filter(custom_filters.StateFilter(bot))


##################
# Running the bot
##################
if __name__ == "__main__":
    logger.warning("if __name__ == __main__")
    bot.polling()
