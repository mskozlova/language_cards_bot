from hashlib import blake2b
import logging
import os
import random
import re

import telebot
from telebot import types
import ydb

from db_functions import *
from word import compare_user_input_with_db, get_translation, get_word, get_overall_score, get_total_trains, format_word_for_listing
from word import format_word_for_group_action, get_word_from_group_action


bot = telebot.TeleBot(os.environ.get("BOT_TOKEN"))
empty_markup = types.ReplyKeyboardRemove()

# TODO: move constants to a separate file
# TODO: move texts to a separate file
logging.getLogger().setLevel(logging.DEBUG)


# YDB initializing
ydb_driver_config = ydb.DriverConfig(
    os.getenv("YDB_ENDPOINT"), os.getenv("YDB_DATABASE"),
    credentials=ydb.credentials_from_env_variables(),
    root_certificates=ydb.load_ydb_root_certificate(),
)

ydb_driver = ydb.Driver(ydb_driver_config)
ydb_driver.wait(fail_fast=True, timeout=30)
pool = ydb.SessionPool(ydb_driver)


# CONSTANTS
TRAIN_STRATEGY_OPTIONS = ["random", "new", "bad", "group"]
TRAIN_DIRECTION_OPTIONS = {"➡️ㅤ": "to", "⬅️ㅤ": "from"}  # invisible symbols to avoid large emoji
TRAIN_COUNT_OPTIONS = ["10", "20", "All"]
TRAIN_HINTS_OPTIONS = ["flashcards", "test", "a****z", "no hints"]
TRAIN_MAX_N_WORDS = 9999;
TRAIN_CORRECT_ANSWER = "✅ㅤ" # invisible symbol to avoid large emoji
TRAIN_WRONG_ANSWER = "❌ {}"
SHOW_WORDS_SORT_OPTIONS = [
    "a-z", "z-a", "score ⬇️", "score ⬆️",
    "n trains ⬇️", "n trains ⬆️", "time added ⬇️", "time added ⬆️"
]
GROUP_ADD_WORDS_SORT_OPTIONS = ["a-z", "time added ⬇️"]
GROUP_ADD_WORDS_PREFIXES = {
    0: "🖤",
    1: "💚",
}
DELETE_ARE_YOU_SURE = {
    "Yes!": True,
    "No..": False,
}


###################
# Command handlers
###################
@bot.message_handler(commands=["help", "start"])
def handle_help(message):
    logging.debug("{} initiated from chat_id {}".format(message.text, message.chat.id))
    try:
        logging.debug("{} initiated, chat_id: {}".format(message.text, message.chat.id))
        bot.send_message(message.chat.id,
                        "Ahoy, sexy! I am a cute little bot for remembering "
                        "words you've learned during your language course. Here's how you can use me:\n\n"
                        "- /help or /start to read this message again.\n"
                        "- /set_language to set current vocabulary "
                        "(you can add multiple and switch between them without erasing the progress).\n"
                        "- /delete_language to delete current language with all data on words, groups, training sessions.\n"
                        "- /add_words to add words to current vocabulary.\n"
                        "- /show_words to print out all words you saved for current language.\n"
                        "- /delete_words to delete some words from current vocabulary.\n"
                        "- /create_group to create new group for words.\n"
                        "- /delete_group to delete one of your groups.\n"
                        "- /show_groups to show your existing groups for current language.\n"
                        "- /group_add_words to add some words from you vocabulary to one of your groups.\n"
                        "- /group_delete_words to delete some words from one of your groups.\n"
                        "- /train to choose training strategy and start training.\n"
                        "- /stop to stop training session without saving the results.\n"
                        "- /forget_me to delete all the information I have about you: languages, words, groups, etc.")
                        # TODO: /share_group, /add_group
    except Exception as e:
        logging.error("help failed", exc_info=e)


@bot.message_handler(commands=["forget_me"])
def handle_forget_me(message):
    markup = types.ReplyKeyboardMarkup(row_width=len(DELETE_ARE_YOU_SURE), resize_keyboard=True, one_time_keyboard=True)
    markup.add(*DELETE_ARE_YOU_SURE.keys(), row_width=len(DELETE_ARE_YOU_SURE))
    bot.send_message(
        message.chat.id,
        "All your languages, words, training sessions and groups will be deleted without any possibility of recovery.\n\n"
        "Are you sure you want to delete all information the bot has about you?",
        reply_markup=markup
    )
    bot.register_next_step_handler(message, process_forget_me)


def process_forget_me(message):
    delete_user(pool, message.chat.id)
    bot.send_message(message.chat.id,
                     "👋 Farewell, my friend! It's sad to see you go.\n"
                     "Check /set_language to make sure you're all cleaned up.")


@bot.message_handler(commands=["set_language"])
def handle_set_language(message):
    try:
        language = get_current_language(pool, message.chat.id)
        if language is not None:
            bot.send_message(message.chat.id, "Your current language is {}.".format(language))
        
        languages = get_available_languages(pool, message.chat.id)
        
        if len(languages) == 0:
            bot.send_message(message.chat.id, "You don't have any languages yet. Write name of a new language to create:")
        else:
            markup = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True, one_time_keyboard=True)
            markup.add(*languages, row_width=3)
            markup.add(*["/cancel"])
            bot.send_message(message.chat.id, "Choose one of your existent languages or type a name for a new one:", reply_markup=markup)
        
        bot.register_next_step_handler(message, process_setting_language, languages=set(languages))
    except Exception as e:
        logging.exception("setting language failed", exc_info=e)


def process_setting_language(message, languages):
    try:
        if message.text == "/cancel":
            bot.send_message(message.chat.id, "Cancelled setting language!", reply_markup=empty_markup)
            return
        
        language = message.text.lower().strip()
        user_info = get_user_info(pool, message.chat.id)
        
        if len(user_info) == 0: # new user!
            bot.send_message(message.chat.id, "Hey! I can see you are new here. Welcome!".format(language), reply_markup=empty_markup)
            create_user(pool, message.chat.id)
            
        if language not in languages:
            bot.send_message(message.chat.id, "You've created a new language {}.".format(language), reply_markup=empty_markup)
            user_add_language(pool, message.chat.id, language)
        
        update_current_lang(pool, message.chat.id, language)
        bot.send_message(message.chat.id, "Language set: {}.\nYou can /add_words to it or /train".format(language), reply_markup=empty_markup)
    except Exception as e:
        logging.exception("processing setting language failed", exc_info=e)


def handle_language_not_set(message):
    bot.send_message(message.chat.id,
                     "Language not set. Set in with command /set_language.")


# TODO: manage possible timeout
# TODO: not allow any special characters apart from "-"
@bot.message_handler(commands=["add_words"])
def handle_add_words(message):
    language = get_current_language(pool, message.chat.id)
    if language is None:
        handle_language_not_set(message)
        return
    try:
        logging.info("Starting adding words!")
        reply_message = bot.reply_to(
            message,
            "First, write new words you want to learn, each on new row.\n"
            "For example:\n"
            "hola\n"
            "gracias\n"
            "adiós\n\n"
            "After that I will ask you to provide translations."
        )
        bot.register_next_step_handler(reply_message, process_adding_words, language=language)
    except Exception as Argument:
        logging.exception("adding words failed")


def process_adding_words(message, language):
    try:
        logging.info("Started translating process, language {}".format(language))
        
        words = list(filter(
            lambda x: len(x) > 0,
            [w.strip().lower() for w in message.text.split("\n")]
        ))
        if len(words) == 0:
            bot.reply_to(
                message,
                "You didn't add anything. Try again /add_words?"
            )
            return
        bot.reply_to(
            message,
            "You've added {} words, now let's translate them one by one. ".format(len(words)) +
            "Type /stop anytime to exit the translation.\n"
            "You can add multiple translations divided by '/', for example:\n"
            "> adiós\n"
            "farewell / goodbye"
        )
        translation_message = bot.send_message(
            message.chat.id,
            "Translate {}".format(words[0])
        )
        bot.register_next_step_handler(translation_message, process_word_translation,
                                       language=language, words=words, translations=[])
    except Exception as Argument:
        logging.exception("processing words addition failed")
        bot.reply_to(
            message,
            "Word adding failed. Try again: /add_words"
        )
        

def process_word_translation(message, language, words, translations):
    try:
        logging.info("Translating word {}".format(words[len(translations)]))
        if message.text != "/stop":
            logging.debug("Adding translation: {}".format(message.text))
            translations.append(json.dumps([m.strip().lower() for m in message.text.split("/")]))    
        
        if len(translations) == len(words) or message.text == "/stop": # translation is over
            logging.debug("Translation is over, len words {}, len translations {}, message {}".format(
                len(words), len(translations),
                message.text
            ))
            update_vocab(pool, message.chat.id, language, list(zip(words, translations)))
            bot.send_message(
                message.chat.id, "Finished! Saved {} words".format(len(translations))
            )
        else:
            logging.debug("Continue translating")
            translation_message = bot.send_message(
                message.chat.id, words[len(translations)]
            )
            bot.register_next_step_handler(translation_message, process_word_translation,
                                           language=language, words=words, translations=translations)
    except Exception as e:
        logging.error("Word translating failed: {}".format(e))


# TODO: delete all unnecessary messages
@bot.message_handler(commands=["show_words"])
def handle_show_words(message):
    language = get_current_language(pool, message.chat.id)
    if language is None:
        handle_language_not_set(message)
        return
    try:
        vocab = get_full_vocab(pool, message.chat.id, language)
        for word in vocab:
            word["score"] = get_overall_score(word)
            word["n_trains"] = get_total_trains(word)
        
        # TODO: make all keyboards one time
        markup = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True, one_time_keyboard=True)
        markup.add(*SHOW_WORDS_SORT_OPTIONS, row_width=2)
        markup.add(telebot.types.KeyboardButton("/exit"))
        
        reply_message = bot.send_message(message.chat.id, "Choose sorting:", reply_markup=markup)
        bot.register_next_step_handler(
            reply_message, process_choose_word_sort,
            words=vocab, original_command="/show_words"
        )
    except Exception as e:
        logging.error("Word showing failed", exc_info=e)


def process_choose_word_sort(message, words, original_command):
    try:
        if message.text == "/exit":
            bot.reply_to(message, "Exited!", reply_markup=empty_markup)
            return
        if message.text not in SHOW_WORDS_SORT_OPTIONS:
            bot.reply_to(message, "This sorting is not supported. Try again {}".format(original_command), reply_markup=empty_markup)
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
        
        process_show_words_batch(message, words=words, batch_size=20, batch_number=0, original_command="/show_words")
    except Exception as e:
        logging.error("process_choose_word_sort failed", exc_info=e)


def process_show_words_batch(message, words, batch_size, batch_number, original_command):
    try:
        if batch_number != 0:
            if message.text == "/exit":
                bot.send_message(message.chat.id, "Exited!", reply_markup=empty_markup)
                return
            if message.text != "/next":
                bot.send_message(message.chat.id, "I don't know this command, try again {}".format(original_command),
                                reply_markup=empty_markup)
                return
        
        words_batch = words[batch_number * batch_size:(batch_number + 1) * batch_size]
        words_formatted = [format_word_for_listing(word) for word in words_batch]
        
        if len(words_batch) == 0:
            bot.send_message(message.chat.id, "This is all the words we have!",
                            reply_markup=empty_markup)
            return
        
        n_pages = len(words) // batch_size
        if len(words) % batch_size > 0:
            n_pages += 1
            
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=True)
        markup.add(*["/exit", "/next"], row_width=2)
        
        bot.send_message(
            message.chat.id,
            "Page {} of {}:\n\n🤍`    %    #  word`\n{}".format(batch_number + 1, n_pages, "\n".join(words_formatted)),
            reply_markup=markup, parse_mode="MarkdownV2"
        )
        
        bot.register_next_step_handler(
            message, process_show_words_batch,
            words=words, batch_size=batch_size, batch_number=batch_number+1, original_command=original_command
        )
    except Exception as e:
        logging.error("showing word batch failed", exc_info=e)


@bot.message_handler(commands=["show_current_language"])
def handle_show_current_languages(message):
    current_language = get_current_language(pool, message.chat.id)
    if current_language is not None:
        bot.reply_to(
            message,
            "Your current language is {}.".format(current_language)
        )
    else:
        handle_language_not_set(message)


@bot.message_handler(commands=["delete_language"])
def handle_delete_language(message):
    try:
        language = get_current_language(pool, message.chat.id)
        if language is None:
            handle_language_not_set(message)
            return
        
        markup = types.ReplyKeyboardMarkup(row_width=len(DELETE_ARE_YOU_SURE), resize_keyboard=True, one_time_keyboard=True)
        markup.add(*DELETE_ARE_YOU_SURE.keys(), row_width=len(DELETE_ARE_YOU_SURE))
        bot.send_message(
            message.chat.id,
            "You are trying to delete language {}\n\n".format(language) +
            "All your words, training sessions and groups for this language will be deleted without any possibility of recovery.\n\n"
            "Are you sure you want to delete language?",
            reply_markup=markup
        )
        bot.register_next_step_handler(message, process_delete_language, language=language)
    except Exception as e:
        logging.error("handle_delete_language failed", exc_info=e)


def process_delete_language(message, language):
    try:
        delete_language(pool, message.chat.id, language)
        bot.send_message(message.chat.id,
                        "Language {} is deleted.\n".format(language) +
                        "Check /set_language to make sure and to set a new language.")
    except Exception as e:
        logging.error("process_delete_language failed", exc_info=e)


# TODO: delete words from groups too
@bot.message_handler(commands=["delete_words"])
def handle_delete_words(message):
    language = get_current_language(pool, message.chat.id)
    if language is None:
        handle_language_not_set(message)
        return
    try:
        reply_message = bot.reply_to(message, "Write words to delete. Each word on new line.")
        bot.register_next_step_handler(reply_message, process_deleting_words, language=language)
    except Exception as e:
        logging.exception("deleting words failed", exc_info=e)


def process_deleting_words(message, language):
    try:
        words = message.text.split("\n")
        existing_words = get_words_from_vocab(pool, message.chat.id, language, words)
        delete_words_from_vocab(pool, message.chat.id, language, words)
        bot.reply_to(
            message,
            "Deleted {} words:\n".format(len(existing_words)) +
            "\n".join([entry["word"] for entry in existing_words]) +
            ("" if len(existing_words) == len(words) else "\n\nOther words are unknown.")
        )
    except Exception as e:
        logging.exception("processing words deleting failed", exc_info=e)


@bot.message_handler(commands=["create_group"])
def handle_create_group(message):
    current_language = get_current_language(pool, message.chat.id)
    if current_language is None:
        handle_language_not_set(message)
        return
    try:
        reply_message = bot.reply_to(
            message,
            "Write new group name. It should consist only of latin letters, digits and underscores.\n"
            "For example, 'nouns_type_3'"
        )
        bot.register_next_step_handler(reply_message, process_group_creation, language=current_language)
    except Exception as e:
        logging.exception("starting creating group failed", exc_info=e)
        

def process_group_creation(message, language):
    # TODO: check latin letters and underscores
    # TODO: check name collisions with shared groups
    try:
        group_name = message.text.strip()
        if len(get_group_by_name(pool, message.chat.id, language, group_name)) > 0:
            bot.reply_to(
                message,
                "You already have a group with that name, please try another: /create_group"
            )
            return
        
        group_id = blake2b(digest_size=10)
        group_key = "{}-{}-{}".format(message.chat.id, language, group_name)
        group_id.update(group_key.encode())
        
        add_group(pool, message.chat.id, language=language,
                group_name=group_name, group_id=group_id.hexdigest(), is_creator=True)
        bot.reply_to(
            message,
            "Group is created! Now add some words: /group_add_words"
        )
    except Exception as e:
        logging.exception("creating group failed", exc_info=e)


def process_show_groups(message, language):
    # TODO: handle large number of groups
    groups = get_all_groups(pool, message.chat.id, language)
    
    if len(groups) == 0:
        bot.reply_to(message, "You don't have any groups yet, try /create_group")
        return
    
    markup = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
    markup.add(*sorted([group["group_name"].decode() for group in groups]), row_width=3)
    markup.add(telebot.types.KeyboardButton("/exit"))
    
    reply_message = bot.send_message(
        message.chat.id,
        "Choose one of your groups\n",
        reply_markup=markup
    )
    return reply_message


@bot.message_handler(commands=["delete_group"])
def handle_delete_group(message):
    current_language = get_current_language(pool, message.chat.id)
    if current_language is None:
        handle_language_not_set(message)
        return
    try:
        reply_message = process_show_groups(message, current_language)
        bot.register_next_step_handler(reply_message, process_group_deletion_check_sure, language=current_language)
    except Exception as e:
        logging.exception("starting creating group failed", exc_info=e)


def process_group_deletion_check_sure(message, language):
    try:
        if message.text == "/exit":
            bot.reply_to(message, "Exited!", reply_markup=empty_markup)
            return
        
        groups = get_group_by_name(pool, message.chat.id, language, message.text)
        
        if len(groups) == 0:
            bot.reply_to(message, "You don't have a group with that name, try again /show_groups",
                         reply_markup=empty_markup)
            return
        
        if not groups[0]["is_creator"]:
            bot.reply_to(message, "You are not a creator of this group, can't edit or delete it.",
                         reply_markup=empty_markup)
            return
        
        group_id = groups[0]["group_id"].decode("utf-8")
        group_name = groups[0]["group_name"].decode("utf-8")
        
        markup = types.ReplyKeyboardMarkup(row_width=len(DELETE_ARE_YOU_SURE), resize_keyboard=True, one_time_keyboard=True)
        markup.add(*DELETE_ARE_YOU_SURE.keys(), row_width=len(DELETE_ARE_YOU_SURE))
        bot.send_message(
            message.chat.id,
            "Are you sure you want to delete group '{}' for language {}?\nThis will NOT affect words in your vocabulary!".format(group_name, language),
            reply_markup=markup
        )
        # TODO: maybe delete words, too?
        bot.register_next_step_handler(message, process_group_deletion, language=language, group_id=group_id, group_name=group_name, is_creator=groups[0]["is_creator"])
    except Exception as e:
        logging.exception("creating group failed", exc_info=e)


def process_group_deletion(message, language, group_id, group_name, is_creator):
    try:
        # TODO: when sharing think of local / global deletions (use is_creator)
        if message.text not in DELETE_ARE_YOU_SURE:
            bot.reply_to(message, "Unknown command, please try again: /delete_group",
                        reply_markup=empty_markup)
            return
        
        if not DELETE_ARE_YOU_SURE[message.text]:
            bot.send_message(
                message.chat.id, "Cancelled group deletion!",
                reply_markup=empty_markup
            )
            return
        
        delete_group(pool, group_id)
        bot.send_message(message.chat.id, "👍 Group '{}' successfully deleted! /show_groups".format(group_name))
    except Exception as e:
        logging.error("process_group_deletion failed", exc_info=e)


@bot.message_handler(commands=["show_groups"])
def handle_show_groups(message):
    try:
        current_language = get_current_language(pool, message.chat.id)
        reply_message = process_show_groups(message, current_language)
        bot.register_next_step_handler(reply_message, process_show_group, language=current_language)
    except Exception as e:
        logging.error("showing groups failed", exc_info=e)
    

def process_show_group(message, language):
    try:
        if message.text == "/exit":
            bot.reply_to(message, "Finished group showing!", reply_markup=empty_markup)
            return
        
        groups = get_group_by_name(pool, message.chat.id, language, message.text)
        
        if len(groups) == 0:
            bot.reply_to(message, "You don't have a group with that name, try again /show_groups",
                         reply_markup=empty_markup)
            return
        
        group_id = groups[0]["group_id"].decode("utf-8")
        group_contents = sorted(get_group_contents(pool, group_id), key=lambda w: w["word"])
        for word in group_contents:
            word["score"] = get_overall_score(word)
            word["n_trains"] = get_total_trains(word)
        
        if len(group_contents) == 0:
            bot.reply_to(message, "This group has no words in it yet, try /group_add_words",
                         reply_markup=empty_markup)
            return
        
        process_show_words_batch(message, group_contents, batch_size=20, batch_number=0, original_command="/show_groups")
    except Exception as e:
        logging.error("showing words of group failed", exc_info=e)
    

@bot.message_handler(commands=["group_add_words"])
def handle_group_add_words(message):
    try:
        current_language = get_current_language(pool, message.chat.id)
        reply_message = process_show_groups(message, current_language)
        bot.register_next_step_handler(reply_message, process_choose_group_to_add_words, language=current_language)
    except Exception as e:
        logging.error("showing groups to add words to failed", exc_info=e)


def get_keyboard_markup(choices, mask, additional_commands=[], row_width=2):
    markup = types.ReplyKeyboardMarkup(row_width=row_width, resize_keyboard=True)
        
    formatted_choices = [
        "{}{}".format(
            GROUP_ADD_WORDS_PREFIXES[mask],
            format_word_for_group_action(entry),
        ) for entry, mask in zip(choices, mask)
    ]
    if len(formatted_choices) % row_width != 0:
        formatted_choices.extend([""] * (row_width - len(formatted_choices) % row_width)) 
    
    markup.add(*formatted_choices, row_width=row_width)
    markup.add(*additional_commands, row_width=len(additional_commands))
    return markup


def save_words_edit_to_group(chat_id, language, group_id, words, action):
    logging.debug("process save_words_edit_to_group: {};".format(action) + ",".join(words))
    
    if len(words) > 0:
        if action == "add":
            add_words_to_group(pool, chat_id, language, group_id, words)
        elif action == "delete":
            delete_words_from_group(pool, chat_id, language, group_id, words)

    return len(words)


def process_words_batch(message, language, group_id, group_name, all_words, current_words,
                        batch_num, batch_size, ok_message=None, chosen_words=set(), is_start=False, action="add"):
    try:
        logging.debug("process_words_batch {}: message={}, batch_num={}, chosen_words={}".format(
            action,
            message.text,
            batch_num,
            chosen_words
        ))
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
                "Choose words to {}. Group '{}', page {} out of {}".format(
                    action,
                    group_name,
                    batch_num + 1,
                    n_batches
                ),
                reply_markup=markup
            )
            bot.register_next_step_handler(
                message, process_words_batch,
                language=language, group_id=group_id, group_name=group_name,
                all_words=all_words, current_words=current_words, chosen_words=chosen_words,
                batch_num=batch_num, batch_size=batch_size, action=action
            )
        elif message.text == "/exit":
            logging.debug("prepare to exit group add words, processing current_words: ", current_words)
            for word, mask in current_words.items():
                if action == "add" and mask == 1:
                    chosen_words.add(word)
                if action == "delete" and mask == 0:
                    chosen_words.add(word)
            n_edited_words = save_words_edit_to_group(message.chat.id, language, group_id, chosen_words, action)
            bot.reply_to(
                message,
                "Finished!\nEdited group {}: {} {} word(s).\n\n".format(group_name, action, n_edited_words) +
                    "\n".join(sorted(list(chosen_words))),
                reply_markup=empty_markup
            )
            return
        elif message.text == "/cancel":
            bot.reply_to(message, "Cancelled! Group was not edited.", reply_markup=empty_markup)
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
                    "That's all the words we have!\nEdited group {}: {} {} word(s).\n\n".format(group_name, action, n_edited_words) +
                        "\n".join(sorted(list(chosen_words))),
                    reply_markup=empty_markup
                )
                return
            
            process_words_batch(message, language=language, group_id=group_id, group_name=group_name,
                                all_words=all_words,
                                current_words=None, batch_num=batch_num, batch_size=batch_size, chosen_words=chosen_words,
                                is_start=True, action=action)

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
                message, process_words_batch,
                language=language, group_id=group_id, group_name=group_name,
                all_words=all_words, current_words=current_words,
                batch_num=batch_num, batch_size=batch_size, ok_message=ok_message,
                chosen_words=chosen_words,
                action=action
            )
            bot.delete_message(message.chat.id, message.id)
        else:
            bot.reply_to(message, "Not a word from the list, ignoring that.")
            bot.register_next_step_handler(message, process_words_batch,
                                        language=language, group_id=group_id, group_name=group_name,
                                        all_words=all_words, current_words=current_words, chosen_words=chosen_words,
                                        batch_num=batch_num, batch_size=batch_size, action=action)
    except Exception as e:
        logging.error("word batch failed", exc_info=e)


def process_choose_group_to_add_words(message, language):
    try:
        if message.text == "/exit":
            bot.reply_to(message, "Exited!", reply_markup=empty_markup)
            return
        
        groups = get_group_by_name(pool, message.chat.id, language, message.text)
        
        if len(groups) == 0:
            bot.reply_to(message, "You don't have a group with that name, try again /show_groups",
                         reply_markup=empty_markup)
            return
        
        if not groups[0]["is_creator"]:
            bot.reply_to(message, "You are not a creator of this group, can't edit or delete it.",
                         reply_markup=empty_markup)
            return
        
        group_id = groups[0]["group_id"].decode("utf-8")
        group_name = groups[0]["group_name"].decode("utf-8")
        
        vocabulary = get_full_vocab(pool, message.chat.id, language)
        words_in_group = set([entry["word"] for entry in get_group_contents(pool, group_id)])
        
        words_to_add = []
        for entry in vocabulary:
            if entry["word"] in words_in_group:
                continue
            words_to_add.append(entry)

        
        if len(words_to_add) == 0:
            bot.reply_to(message, "There're no more words to add to this group.")
            return
        
        markup = types.ReplyKeyboardMarkup(row_width=4, one_time_keyboard=True, resize_keyboard=True)
        markup.add(*GROUP_ADD_WORDS_SORT_OPTIONS, row_width=4)
        markup.add(telebot.types.KeyboardButton("/exit"))
        
        reply_message = bot.send_message(message.chat.id, "Choosing sorting:", reply_markup=markup)
        bot.register_next_step_handler(reply_message, process_choose_sorting_to_add_words, language=language,
                                       group_id=group_id, group_name=group_name, vocabulary=words_to_add)
    except Exception as e:
        logging.error("group adding words failed", exc_info=e)
        

def process_choose_sorting_to_add_words(message, language, group_id, group_name, vocabulary):
    try:
        logging.debug("process_choose_sorting_to_add_words")
        if message.text == "/exit":
            bot.reply_to(message, "Exited!", reply_markup=empty_markup)
            return
        
        if message.text not in GROUP_ADD_WORDS_SORT_OPTIONS:
            bot.reply_to(message, "This sorting is not supported, try again /group_add_words", reply_markup=empty_markup)
            return
        
        if message.text == "a-z":
            vocabulary = sorted(vocabulary, key=lambda x: x["translation"])
        elif message.text == "time added ⬇️":
            vocabulary = sorted(vocabulary, key=lambda x: x["added_timestamp"])[::-1]
   
        process_words_batch(message, language=language, group_id=group_id, group_name=group_name,
                            all_words=vocabulary, current_words=None, chosen_words=set(),
                            batch_num=0, batch_size=10, is_start=True)
    except Exception as e:
        logging.error("choose sorting for group word addition failed", exc_info=e)


@bot.message_handler(commands=["group_delete_words"])
def handle_group_delete_words(message):
    try:
        current_language = get_current_language(pool, message.chat.id)
        reply_message = process_show_groups(message, current_language)
        bot.register_next_step_handler(reply_message, process_choose_group_to_delete_words, language=current_language)
    except Exception as e:
        logging.error("showing groups to delete words to failed", exc_info=e)


def process_choose_group_to_delete_words(message, language):
    try:
        logging.debug("Start deleting words from group")
        if message.text == "/exit":
            bot.reply_to(message, "Exited!", reply_markup=empty_markup)
            return
        
        groups = get_group_by_name(pool, message.chat.id, language, message.text)
        
        if len(groups) == 0:
            bot.reply_to(message, "You don't have a group with that name, try again /show_groups",
                         reply_markup=empty_markup)
            return
        
        if not groups[0]["is_creator"]:
            bot.reply_to(message, "You are not a creator of this group, can't edit or delete it.",
                         reply_markup=empty_markup)
            return
        
        group_id = groups[0]["group_id"].decode("utf-8")
        group_name = groups[0]["group_name"].decode("utf-8")
        
        words_in_group = sorted(get_group_contents(pool, group_id), key=lambda entry: entry["translation"])
        
        if len(words_in_group) == 0:
            bot.reply_to(message, "There're no words in this group.")
            return

        process_words_batch(message, language=language,
                            group_id=group_id, group_name=group_name, all_words=words_in_group, current_words=dict(),
                            chosen_words=set(), batch_num=0, batch_size=10, is_start=True, action="delete")
    except Exception as e:
        logging.error("group deleting words failed", exc_info=e)


@bot.message_handler(commands=["train"])
def handle_train(message):
    current_language = get_current_language(pool, message.chat.id)
    if current_language is None:
        handle_language_not_set(message)
        return
    try:
        markup = types.ReplyKeyboardMarkup(row_width=4, one_time_keyboard=True, resize_keyboard=True)
        markup.add(*TRAIN_STRATEGY_OPTIONS, row_width=4)
        markup.add(telebot.types.KeyboardButton("/cancel"))
        reply_message = bot.send_message(
            message.chat.id,
            "Choose training strategy.\n"
            "Now available:\n\n"
            "- random - simply random words\n"
            "- new - only words that you've seen not more than 2 times\n"
            "- bad - only words with weak score\n"
            "- group - words from a particular group",
            reply_markup=markup
        )
        session_info = {"language": current_language}
        messages = [reply_message]
        bot.register_next_step_handler(reply_message, process_choose_strategy, session_info=session_info, messages=messages)
    except Exception as Argument:
        logging.exception("starting train failed")


def init_direction_choice(message, session_info, messages):
    markup = types.ReplyKeyboardMarkup(row_width=len(TRAIN_DIRECTION_OPTIONS), one_time_keyboard=True, resize_keyboard=True)
    markup.add(*list(TRAIN_DIRECTION_OPTIONS.keys()), row_width=len(TRAIN_DIRECTION_OPTIONS))
    markup.add(telebot.types.KeyboardButton("/cancel"))
    reply_message = bot.send_message(
        message.chat.id,
        "Choose training direction: to ➡️, or from ⬅️ your current language",
        reply_markup=markup
    )
    messages.extend([reply_message])
    bot.register_next_step_handler(reply_message, process_choose_direction, session_info=session_info, messages=messages)
    

def process_choose_group_for_training(message, session_info, messages):
    if message.text == "/exit":
        bot.reply_to(message, "Cancelled training, come back soon and /train again!", reply_markup=empty_markup)
        return
        
    groups = get_group_by_name(pool, message.chat.id, session_info["language"], message.text)
    if len(groups) == 0:
        bot.reply_to(message, "You don't have a group with that name, try again /train",
                     reply_markup=empty_markup)
        return
    
    group_id = groups[0]["group_id"].decode("utf-8")
    session_info["group_name"] = message.text
    session_info["group_id"] = group_id
    messages.append(message)
    
    init_direction_choice(message, session_info, messages)


def process_choose_strategy(message, session_info, messages):
    if message.text == "/cancel":
        bot.reply_to(message, "Cancelled training, come back soon and /train again!", reply_markup=empty_markup)
        return
    if message.text not in TRAIN_STRATEGY_OPTIONS:
        bot.reply_to(message, "This strategy is not supported. Try again /train", reply_markup=empty_markup)
        return
    session_info["strategy"] = message.text
    messages.extend([message])
    
    if message.text == "group":
        reply_message = process_show_groups(message, session_info["language"])
        messages.extend([reply_message])
        bot.register_next_step_handler(reply_message, process_choose_group_for_training,
                                       session_info=session_info, messages=messages)
    else:
        init_direction_choice(message, session_info, messages)


def process_choose_direction(message, session_info, messages):
    if message.text == "/cancel":
        bot.reply_to(message, "Cancelled training, come back soon and /train again!", reply_markup=empty_markup)
        return
    if message.text not in TRAIN_DIRECTION_OPTIONS.keys():
        bot.reply_to(message, "This direction is not supported. Try again /train", reply_markup=empty_markup)
        return

    markup = types.ReplyKeyboardMarkup(row_width=len(TRAIN_COUNT_OPTIONS), one_time_keyboard=True, resize_keyboard=True)
    markup.add(*TRAIN_COUNT_OPTIONS, row_width=len(TRAIN_COUNT_OPTIONS))
    markup.add(telebot.types.KeyboardButton("/cancel"))
    reply_message = bot.send_message(
        message.chat.id,
        "Choose duration of your training. You can also type in any number.",
        reply_markup=markup
    )
    session_info["direction"] = TRAIN_DIRECTION_OPTIONS[message.text]
    messages.extend([message, reply_message])
    bot.register_next_step_handler(reply_message, process_choose_duration, session_info, messages=messages)


def process_choose_duration(message, session_info, messages):
    if message.text == "/cancel":
        bot.reply_to(message, "Cancelled training, come back soon and /train again!", reply_markup=empty_markup)
        return
    if not message.text.isdigit() and message.text not in TRAIN_COUNT_OPTIONS:
        bot.reply_to(message, "This duration is not supported. Try again /train", reply_markup=empty_markup)
        return

    markup = types.ReplyKeyboardMarkup(row_width=len(TRAIN_HINTS_OPTIONS), one_time_keyboard=True, resize_keyboard=True)
    markup.add(*TRAIN_HINTS_OPTIONS, row_width=len(TRAIN_HINTS_OPTIONS))
    markup.add(telebot.types.KeyboardButton("/cancel"))
    reply_message = bot.send_message(
        message.chat.id,
        "Choose hints for your training.\n"
        "Training with hints will not affect you word scores. Choose 'no hints' to track your progress.",
        reply_markup=markup
    )
    session_info["duration"] = int(message.text) if message.text.isdigit() else TRAIN_MAX_N_WORDS
    messages.extend([message, reply_message])
    bot.register_next_step_handler(reply_message, process_choose_hints, session_info, messages=messages)


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
    try:
        if message.text == "/stop":
            bot.send_message(
                message.chat.id,
                "Session stopped, results not saved.\nLet's /train again?",
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
                    TRAIN_CORRECT_ANSWER,
                    reply_markup=empty_markup
                )
            else:
                bot.send_message(
                    message.chat.id,
                    TRAIN_WRONG_ANSWER.format(
                        get_translation(word, session_info["direction"])
                    ),
                    reply_markup=empty_markup
                )

        if step == len(words): # training complete
            # TODO: different messages for different results
            if session_info["hints"] == "no hints":
                logging.debug("setting training session scores for chat_id {}, scores: {}".format(message.chat.id, scores))
                set_training_scores(
                    pool, message.chat.id, session_info["session_id"],
                    list(range(1, len(words) + 1)), scores
                )
                logging.debug("updating final scores")
                update_final_scores(pool, message.chat.id, session_info)
            else:
                bot.send_message(
                    message.chat.id, "Scores are not saved because hints were used."
                )
            bot.send_message(
                message.chat.id,
                "Score: {} / {}\n🎉 Training complete!\nLet's /train again?".format(sum(scores), len(words)),
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
            reply_message, get_train_step,
            words=words, session_info=session_info, step=step+1, scores=scores
        )
    except Exception as e:
        logging.error("getting train step failed", exc_info=e)


def process_choose_hints(message, session_info, messages):
    try:
        if message.text == "/cancel":
            bot.reply_to(message, "Cancelled training, come back soon and /train again!", reply_markup=empty_markup)
            return
        if message.text not in TRAIN_HINTS_OPTIONS:
            bot.reply_to(message, "These hints are not supported. Try again /train",
                        reply_markup=empty_markup)
            return
        
        session_info["hints"] = message.text
        session_info["session_id"] = get_new_session_id()
        messages.append(message)
        
        init_training_session(pool, message.chat.id, session_info)
        logging.debug("initiating train session for chat_id {}".format(message.chat.id))
        if session_info["strategy"] != "group":
            create_training_session(pool, message.chat.id, session_info)
        else:
            create_group_training_session(pool, message.chat.id, session_info)
        
        words = get_training_words(pool, message.chat.id, session_info)
        
        if len(words) == 0:
            bot.send_message(
                message.chat.id,
                "There are no words satisfying your parameters, try choosing something else: /train",
                reply_markup=empty_markup
            )
            return
        
        bot.send_message(
            message.chat.id,
            "Starting training.\n" +
            "Strategy: {}\nDuration: {}\nDirection: {}\nHints: {}".format(
                session_info["strategy"], len(words),
                session_info["direction"], session_info["hints"]
            ) + (
                "\n\nGroup name: {}".format(session_info["group_name"]) if "group_name" in session_info else ""
            ),
            reply_markup=empty_markup
        )
        if len(words) < session_info["duration"] and session_info["duration"] != TRAIN_MAX_N_WORDS:
            bot.send_message(
                message.chat.id,
                "(I have found fewer words than you have requested)",
                reply_markup=empty_markup
            )
        # delete all technical messages if training init is successful
        for m in messages:
            bot.delete_message(message.chat.id, m.id)
        get_train_step(message=message, words=words, session_info=session_info, step=0, scores=[])
    
    except Exception as e:
        logging.error("creating train session failed", exc_info=e)
        return


##################
# Running the bot
##################
if __name__ == "__main__":
    logging.info("starting bot")
    bot.remove_webhook()
    bot.polling()
    logging.info("program exited")
