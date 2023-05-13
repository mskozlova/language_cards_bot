from hashlib import blake2b
import logging
import os
import random

import telebot
from telebot import types
import ydb

from db_functions import *
from word import compare_user_input_with_db, get_translation, get_word


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
    # user = get_user(message.chat.id)
    try:
        language = message.text.lower().strip()
        # user.set_current_lang(language)
        update_current_lang(pool, message.chat.id, language)
        bot.reply_to(message, "Language set: {}.\nYou can /add_words to it or /train".format(language))
    except Exception as Argument:
        logging.exception("processing setting language failed")


def handle_language_not_set(message):
    bot.send_message(message.chat.id,
                     "Language not set. Set in with command /set_language.")


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
        

@bot.message_handler(commands=["show_words"])
def handle_show_words(message):
    language = get_current_language(pool, message.chat.id)
    if language is None:
        handle_language_not_set(message)
        return
    try:
        logging.debug("Showing all words, chat {}".format(message.chat.id))
        vocab = get_full_vocab(pool, message.chat.id, language)
        vocab = sorted(vocab, key=lambda entry: entry["word"])
        words = [
            "{} - {}".format(
                entry["word"],
                " / ".join(json.loads(entry["translation"]))
            ) for entry in vocab
        ]
        bot.reply_to(
            message,
            "Your words for {} language:\n\n".format(language) +
            "\n".join(words)
        )
    except Exception as e:
        logging.error("Word showing failed: {}".format(e))
    


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
    
    markup = types.ReplyKeyboardMarkup(row_width=3)
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
        group_contents = get_group_contents(pool, group_id)
        
        if len(group_contents) == 0:
            bot.reply_to(message, "This group has no words in it yet, try /group_add_words",
                         reply_markup=empty_markup)
            return
        
        words = [
            "{} - {}".format(
                entry["word"],
                " / ".join(json.loads(entry["translation"]))
            ) for entry in group_contents
        ]
        bot.reply_to(
            message,
            "Your words for {} language, group {}:\n\n".format(language, message.text) +
            "\n".join(words),
            reply_markup=empty_markup
        )
    
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
    # TODO: fails if there are no words
    current_language = get_current_language(pool, message.chat.id)
    if current_language is None:
        handle_language_not_set(message)
        return
    try:
        markup = types.ReplyKeyboardMarkup(row_width=3)
        markup.add(telebot.types.KeyboardButton("random"))
        markup.add(telebot.types.KeyboardButton("new"))
        markup.add(telebot.types.KeyboardButton("bad"))
        reply_message = bot.send_message(
            message.chat.id,
            "Choose training strategy.\n"
            "Now available:\n\n"
            "- random - simply random words\n"
            "- new - only words that you've seen not more than 2 times\n"
            "- bad - only words with weak score",
            reply_markup=markup
        )
        bot.register_next_step_handler(reply_message, process_choose_strategy)
    except Exception as Argument:
        logging.exception("starting train failed")


def process_choose_strategy(message):
    if message.text not in ("random", "new", "bad"):
        bot.reply_to(message, "This strategy is not supported. Try again /train", reply_markup=empty_markup)
        return
    session_id = get_new_session_id()
    language = get_current_language(pool, message.chat.id)
    init_training_session(pool, message.chat.id, language, session_id, message.text)
    markup = types.ReplyKeyboardMarkup(row_width=2)
    markup.add(telebot.types.KeyboardButton("5 to"))
    markup.add(telebot.types.KeyboardButton("10 to"))
    markup.add(telebot.types.KeyboardButton("5 from"))
    markup.add(telebot.types.KeyboardButton("10 from"))
    reply_message = bot.send_message(
        message.chat.id,
        "Choose duration of training and order to/from your set language.",
        reply_markup=markup
    )
    bot.register_next_step_handler(reply_message, process_choose_length_and_order)


def process_choose_length_and_order(message):
    if len(message.text.split(" ")) != 2 or message.text.split(" ")[1] not in ("to", "from"):
        bot.reply_to(message, "This length and order is not supported. Try again /train",
                     reply_markup=empty_markup)
        return
    session_id = get_current_session_id(pool, message.chat.id)
    length, order = message.text.split(" ")
    set_session_order_and_length(pool, message.chat.id, session_id, order, length)
    markup = types.ReplyKeyboardMarkup(row_width=1)
    markup.add(telebot.types.KeyboardButton("no hints"))
    markup.add(telebot.types.KeyboardButton("a****z"))
    markup.add(telebot.types.KeyboardButton("test"))
    reply_message = bot.send_message(
        message.chat.id,
        "Choose hints.",
        reply_markup=markup
    )
    bot.register_next_step_handler(reply_message, process_choose_hints)


def get_az_hint(word):
    if len(word) <= 4:
        return "*" * len(word)
    return word[0] + "*" * (len(word) - 2) + word[-1]


def format_train_message(word, translation, hints_type):
    if hints_type != "a****z":
        return word
    else:
        return "{}\nHint: {}".format(
            word,
            get_az_hint(translation)
        )


def format_train_buttons(translation, hints, hints_type):
    if hints_type != "test":
        return empty_markup
    all_words_list = hints + [translation, ]
    random.shuffle(all_words_list)
    markup = types.ReplyKeyboardMarkup(
        row_width=2
    )
    markup.add(*[telebot.types.KeyboardButton(w.split("/")[0]) for w in all_words_list])
    return markup


def process_choose_hints(message):
    if message.text not in ("no hints", "a****z", "test"):
        bot.reply_to(message, "These hints are not supported. Try again /train",
                     reply_markup=empty_markup)
        return
    session_id = get_current_session_id(pool, message.chat.id)
    set_session_hints(pool, message.chat.id, session_id, message.text)
    session_info = get_session_info(pool, message.chat.id, session_id)
    current_lang = get_current_language(pool, message.chat.id)
    create_training_session(pool, message.chat.id, session_id, current_lang, session_info["length"],
                            session_info["strategy"].decode("utf-8"), session_info["order"].decode("utf-8"))
    update_length(pool, message.chat.id, session_id)
    session_info = get_session_info(pool, message.chat.id, session_id)
    bot.reply_to(message,
                 "Starting training.\n" +
                 "Strategy: {}\nLength: {}\nLanguage order: {}\nHints: {}".format(
                     session_info["strategy"].decode("utf-8"), session_info["length"],
                     session_info["order"].decode("utf-8"), session_info["hints"].decode("utf-8")
                 ),
                 reply_markup=empty_markup)
    try:
        next_word = get_next_word(pool, message.chat.id, session_id)
        hints = get_test_hints(pool, message.chat.id, session_id, next_word["word"], current_lang)
        session_info = get_session_info(pool, message.chat.id, session_id)
        reply_message = bot.send_message(
            message.chat.id,
            format_train_message(
                get_word(next_word, next_word["order"].decode("utf-8")),
                get_translation(next_word, next_word["order"].decode("utf-8")),
                session_info["hints"].decode("utf-8")
            ),
            reply_markup=format_train_buttons(
                get_translation(next_word, next_word["order"].decode("utf-8")),
                [get_translation(hint, next_word["order"].decode("utf-8")) for hint in hints],
                session_info["hints"].decode("utf-8")
            )
        )
        bot.register_next_step_handler(reply_message, process_translation)
    except IndexError:
        bot.reply_to(message, "There are no words in this strategy. Try another.\n/train")


def process_translation(message):
    session_id = get_current_session_id(pool, message.chat.id)
    current_lang = get_current_language(pool, message.chat.id)
    try:
        next_word = get_next_word(pool, message.chat.id, session_id)
        if message.text == "/stop":
            bot.reply_to(message, "Session stopped, results not saved.\nLet's /train again?",
                         reply_markup=empty_markup)
            return

        score = compare_user_input_with_db(message.text, next_word, next_word["order"].decode("utf-8"))
        update_score(pool, message.chat.id, session_id, score)
        current_scores = get_scores(pool, message.chat.id, session_id)
        if score == 1:
            bot.send_message(
                message.chat.id,
                "Correct! Score: {}/{}".format(int(current_scores["successes"]), current_scores["words"])
            )
        else:
            bot.send_message(
                message.chat.id,
                "Wrong! Correct translation: {}\n".format(get_translation(next_word, next_word["order"].decode("utf-8"))) +
                "Score: {}/{}".format(int(current_scores["successes"]), current_scores["words"])
            )

        next_word = get_next_word(pool, message.chat.id, session_id)
        hints = get_test_hints(pool, message.chat.id, session_id, next_word["word"], current_lang)
        session_info = get_session_info(pool, message.chat.id, session_id)
        reply_message = bot.send_message(
            message.chat.id,
            format_train_message(
                get_word(next_word, next_word["order"].decode("utf-8")),
                get_translation(next_word, next_word["order"].decode("utf-8")),
                session_info["hints"].decode("utf-8")
            ),
            reply_markup=format_train_buttons(
                get_translation(next_word, next_word["order"].decode("utf-8")),
                [get_translation(hint, next_word["order"].decode("utf-8")) for hint in hints],
                session_info["hints"].decode("utf-8")
            )
        )
        bot.register_next_step_handler(reply_message, process_translation)
    except IndexError:
        cleanup_scores(pool, message.chat.id)
        update_final_scores(pool, message.chat.id, session_id)
        bot.reply_to(message, "Training complete!\nLet's /train again?",
                     reply_markup=empty_markup)


##################
# Running the bot
##################
if __name__ == "__main__":
    logging.info("starting bot")
    bot.remove_webhook()
    bot.polling()
    logging.info("program exited")
