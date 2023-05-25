from hashlib import blake2b
import logging
import os
import random

import telebot
from telebot import types
import ydb

from db_functions import *
from word import compare_user_input_with_db, get_translation, get_word, get_overall_score, get_total_trains, format_word_for_listing


bot = telebot.TeleBot(os.environ.get("BOT_TOKEN"))
empty_markup = types.ReplyKeyboardRemove()

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
TRAIN_HINTS_OPTIONS = ["no hints", "a****z", "test"]
TRAIN_MAX_N_WORDS = 9999;
TRAIN_CORRECT_ANSWER = "✅ㅤ" # invisible symbol to avoid large emoji
TRAIN_WRONG_ANSWER = "❌ {}"
SHOW_WORDS_SORT_OPTIONS = ["a-z", "z-a", "score ⬇️", "score ⬆️", "n trains ⬇️", "n trains ⬆️"] # TODO: added time


###################
# Command handlers
###################
@bot.message_handler(commands=["help", "start"])
def handle_help(message):
    bot.send_message(message.chat.id,
                     "Ahoy, sexy! I am a cute little bot for remembering "
                     "words you've learned during your language course. Here's how you can use me:\n\n"
                     "- /help or /start to read this message again.\n"
                     "- /set_language to set current vocabulary "
                     "(you can add multiple and switch between them without erasing the progress).\n"
                     "- /show_languages to see the list of your languages.\n"
                     "- /add_words to add words to current vocabulary.\n"
                     "- /show_words to print out all words you saved for current language.\n"
                     "- /delete_words to delete some words from current vocabulary.\n"
                     "- /create_group to create new group for words.\n"
                     "- /show_groups to show your existing groups for current language.\n"
                     "- /group_add_words to add some words from you vocabulary to one of your groups.\n"
                     # TODO "- /group_delete_words to delete some words from one of your groups.\n"
                     "- /train to choose training strategy and start training.\n"
                     "- /stop to stop training session without saving the results.\n")
                     #"- /forget_me to delete all the information I have about you.\n")
    # TODO: all commands


# @bot.message_handler(commands=["forget_me"])
# def handle_forget_me(message):
#     delete_user(message.chat.id)
#     bot.send_message(message.chat.id,
#                      "Farewell, my friend! Come back soon.")


@bot.message_handler(commands=["set_language"])
def handle_set_language(message):
    try:
        reply_message = bot.reply_to(message, "Write language code.")
        bot.register_next_step_handler(reply_message, process_setting_language)
    except Exception as Argument:
        logging.exception("setting language failed")


def process_setting_language(message):
    try:
        language = message.text.lower().strip()
        update_current_lang(pool, message.chat.id, language)
        bot.reply_to(message, "Language set: {}.\nYou can /add_words to it or /train".format(language))
    except Exception as Argument:
        logging.exception("processing setting language failed")


def handle_language_not_set(message):
    bot.send_message(message.chat.id,
                     "Language not set. Set in with command /set_language.")


# TODO: manage possible timeout
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
        # language = get_current_language(pool, message.chat.id)
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



@bot.message_handler(commands=["show_languages"])
def handle_show_languages(message):
    languages = get_available_languages(pool, message.chat.id)
    if len(languages) == 0:
        bot.reply_to(message, "You don't have any languages.")
    elif len(languages) == 1:
        bot.reply_to(
            message,
            "Here is your language: {}.".format(languages[0])
        )
    else:
        bot.reply_to(
            message,
            "Here are your languages: {}.".format(
                ", ".join(languages)
            )
        )


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


# @bot.message_handler(commands=["delete_language"])
# def handle_delete_language(message):
#     user = get_user(message.chat.id)
#     language = user.get_current_lang()
#     if language is None:
#         handle_language_not_set(message)
#         return
#
#     result = user.delete_language(language)
#     if result:
#         delete_language_from_vocab(pool, user)
#         update_user(pool, user)
#         bot.reply_to(message, "Successfully deleted language: {}.".format(language))
#         logging.info("successfully deleted language: {}".format(language))
#     else:
#         bot.reply_to(message, "You don't have language {}.".format(language))


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


def get_keyboard_markup(choices, additional_commands=[], row_width=3):
    markup = types.ReplyKeyboardMarkup(row_width=row_width, resize_keyboard=True)
    if len(choices) % row_width != 0:
        choices.extend([""] * (row_width - len(choices) % row_width))
    markup.add(*choices, row_width=row_width)
    markup.add(*additional_commands, row_width=row_width)
    return markup


def save_words_to_group(chat_id, language, group_id, words):
    original_words = [word.split(" - ")[0] for word in words]
    logging.debug(",".join(original_words))
    add_words_to_group(pool, chat_id, language, group_id, original_words)


# TODO: do not delete used words, but change the to blank buttons
def process_words_batch(message, language, group_id, group_name, all_words, current_words,
                        batch_num, batch_size, is_start=False, chosen_words=set()):
    try:
        logging.debug("process_words_batch: message={}, batch_num={}, chosen_words={}".format(
            message.text,
            batch_num,
            ",".join(chosen_words)
        ))
        if is_start: # new page
            markup = get_keyboard_markup(
                all_words[batch_num * batch_size:(batch_num + 1) * batch_size],
                ["/cancel", "/exit", "/next"]
            )
            current_words = set(
                all_words[batch_num * batch_size:(batch_num + 1) * batch_size]
            )
            message = bot.send_message(
                message.chat.id,
                "Choose words for group {}, page {} out of {}".format(
                    group_name,
                    batch_num + 1,
                    len(all_words) // batch_size
                ),
                reply_markup=markup
            )
            bot.register_next_step_handler(message, process_words_batch,
                                        language=language, group_id=group_id, group_name=group_name,
                                        all_words=all_words, current_words=current_words,
                                        batch_num=batch_num, batch_size=batch_size, chosen_words=chosen_words)
        elif message.text == "/exit":
            if len(chosen_words) > 0:
                save_words_to_group(message.chat.id, language, group_id, chosen_words)
            bot.reply_to(message, "Finished! Saved {} words to {} group".format(len(chosen_words), group_name),
                        reply_markup=empty_markup)
            return
        elif message.text == "/cancel":
            bot.reply_to(message, "Cancelled! Saved no words.", reply_markup=empty_markup)
            return
        elif message.text == "/next":
            batch_num += 1
            if batch_num * batch_size >= len(all_words):
                if len(chosen_words) > 0:
                    save_words_to_group(message.chat.id, language, group_id, chosen_words)
                bot.reply_to(
                    message,
                    "That's all the words we have! Saved {} words to {} group".format(len(chosen_words), group_name),
                    reply_markup=empty_markup
                )
                return
            
            process_words_batch(message, language=language, group_id=group_id, group_name=group_name,
                                all_words=all_words,
                                current_words=None, batch_num=batch_num, batch_size=batch_size,
                                is_start=True, chosen_words=chosen_words)

        elif message.text in current_words:
            chosen_words.add(message.text)
            bot.register_next_step_handler(message, process_words_batch,
                                        language=language, group_id=group_id, group_name=group_name,
                                        all_words=all_words, current_words=current_words,
                                        batch_num=batch_num, batch_size=batch_size, chosen_words=chosen_words)
        else:
            bot.reply_to(message, "Not a word from the list, ignoring that.")
            bot.register_next_step_handler(message, process_words_batch,
                                        language=language, group_id=group_id, group_name=group_name,
                                        all_words=all_words, current_words=current_words,
                                        batch_num=batch_num, batch_size=batch_size, chosen_words=chosen_words)
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
            bot.reply_to(message, "You are not a creator of this group, can't edit it.",
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
            words_to_add.append(
                "{} - {}".format(
                    entry["word"],
                    " / ".join(json.loads(entry["translation"]))
                )
            )
        
        if len(words_to_add) == 0:
            bot.reply_to(message, "There're no more words to add to this group.")
            return
        process_words_batch(message, language=language, group_id=group_id, group_name=group_name,
                            all_words=words_to_add, current_words=None,
                            batch_num=0, batch_size=9, is_start=True)
    except Exception as e:
        logging.error("group adding words failed", exc_info=e)


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
    if hints_type != "a****z":
        return word
    else:
        return "{}\n{}".format(
            word,
            get_az_hint(translation)
        )


def format_train_buttons(translation, hints, hints_type):
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
        if step != 0: # first iteration
            word = words[step - 1]
            is_correct = compare_user_input_with_db(
                message.text,
                word,
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
                set_training_scores(
                    pool, message.chat.id, session_info["session_id"],
                    list(range(1, len(words) + 1)), scores
                )
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
            )
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
