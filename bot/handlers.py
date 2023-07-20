import json

from telebot import TeleBot
from telebot.types import Message

import database.model as db_model
from database.ydb_settings import pool
from logs import logger, logged_execution
import user_interaction.options as options
import user_interaction.texts as texts
from word import Word

import bot.constants as constants
import bot.keyboards as keyboards
import bot.states as states


@logged_execution
def handle_help(message: Message, bot: TeleBot):
    bot.send_message(message.chat.id, texts.help_message)


@logged_execution
def handle_stop(message: Message, bot: TeleBot):
    bot.delete_state(message.from_user.id, message.chat.id)
    bot.send_message(message.chat.id, texts.stop_message)


@logged_execution
def handle_forget_me(message: Message, bot: TeleBot):
    markup = keyboards.get_reply_keyboard(options.delete_are_you_sure)
    bot.set_state(message.from_user.id, states.ForgetMeState.init, message.chat.id)
    bot.send_message(message.chat.id, texts.forget_me_warning, reply_markup=markup)


# forget me
@logged_execution
def process_forget_me(message: Message, bot: TeleBot):
    bot.delete_state(message.from_user.id, message.chat.id)

    if message.text not in options.delete_are_you_sure:
        bot.reply_to(message, texts.unknown_command_short)
        return
    
    if options.delete_are_you_sure[message.text]:
        db_model.delete_user(pool, message.chat.id)
        bot.send_message(message.chat.id, texts.forget_me_final)
    else:
        bot.send_message(message.chat.id, texts.cancel_short)


@logged_execution
def handle_unknown(message: Message, bot: TeleBot):
    # bot.reply_to(message, texts.unknown_message)
    logger.warning(f"Unknown message! chat_id: {message.chat.id}, message: {message.text}")


# set language

# TODO: check language name (same as group name)
@logged_execution
def handle_set_language(message: Message, bot: TeleBot):
    language = db_model.get_current_language(pool, message.chat.id)
    if language is not None:
        bot.send_message(message.chat.id, texts.current_language.format(language))
    
    languages = db_model.get_available_languages(pool, message.chat.id)
    
    if len(languages) == 0:
        bot.send_message(message.chat.id, texts.no_languages_yet)
    else:
        markup = keyboards.get_reply_keyboard(languages, ["/cancel"])
        bot.send_message(message.chat.id, texts.set_language, reply_markup=markup)
    
    bot.set_state(message.from_user.id, states.SetLanguageState.init, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["languages"] = languages


@logged_execution
def process_setting_language_cancel(message: Message, bot: TeleBot):
    bot.delete_state(message.from_user.id, message.chat.id)
    bot.send_message(message.chat.id, texts.set_language_cancel)


@logged_execution
def process_setting_language(message: Message, bot: TeleBot):
    language = message.text.lower().strip()
    user_info = db_model.get_user_info(pool, message.chat.id)
    
    if len(user_info) == 0: # new user!
        bot.send_message(message.chat.id, texts.welcome)
        db_model.create_user(pool, message.chat.id)
    
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        if language not in data["languages"]:
            bot.send_message(
                message.chat.id,
                texts.new_language_created.format(language),
            )
            db_model.user_add_language(pool, message.chat.id, language)

    bot.delete_state(message.from_user.id, message.chat.id)

    db_model.update_current_lang(pool, message.chat.id, language)
    bot.send_message(message.chat.id, texts.language_is_set.format(language))


@logged_execution
def handle_language_not_set(message, bot):
    bot.send_message(message.chat.id, texts.no_language_is_set)


# add words

# TODO: not allow any special characters apart from "-"
# TODO: is there still timeout ?
@logged_execution
def handle_add_words(message: Message, bot: TeleBot):
    language = db_model.get_current_language(pool, message.chat.id)
    if language is None:
        handle_language_not_set(message, bot)
        return
    
    bot.set_state(message.from_user.id, states.AddWordsState.add_words, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["language"] = language
    
    bot.reply_to(message, texts.add_words_instruction_1)


@logged_execution
def process_adding_words(message: Message, bot: TeleBot):
    words = list(filter(
        lambda x: len(x) > 0,
        [w.strip().lower() for w in message.text.split("\n")]
    ))
    if len(words) == 0:
        bot.reply_to(message, texts.add_words_none_added)
        bot.delete_state(message.from_user.id, message.chat.id)
        return
    
    bot.reply_to(message, texts.add_words_instruction_2.format(words))
    bot.send_message(
        message.chat.id,
        texts.add_words_translate.format(words[0])
    )
    
    bot.set_state(message.from_user.id, states.AddWordsState.translate, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["words"] = words
        data["translations"] = []


@logged_execution
def process_word_translation_stop(message: Message, bot: TeleBot):
    bot.delete_state(message.from_user.id, message.chat.id)
    bot.send_message(message.chat.id, texts.add_words_cancelled)
        

@logged_execution
def process_word_translation(message: Message, bot: TeleBot):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["translations"].append(json.dumps([m.strip().lower() for m in message.text.split("/")]))
        
        if len(data["translations"]) == len(data["words"]): # translation is over
            db_model.update_vocab(pool, message.chat.id, data["language"], data["words"], data["translations"])
            bot.send_message(
                message.chat.id, texts.add_words_finished.format(len(data["words"]))
            )
            bot.delete_state(message.from_user.id, message.chat.id)
        else:
            bot.send_message(
                message.chat.id, data["words"][len(data["translations"])]
            )


# show words

@logged_execution
def handle_show_words(message: Message, bot: TeleBot):
    language = db_model.get_current_language(pool, message.chat.id)
    if language is None:
        handle_language_not_set(message, bot)
        return

    vocab = db_model.get_full_vocab(pool, message.chat.id, language)
    for entry in vocab:
        word = Word(entry)
        entry["score"] = word.get_overall_score()
        entry["n_trains"] = word.get_total_trains()
    
    # TODO: make all keyboards one time
    markup = keyboards.get_reply_keyboard(options.show_words_sort_options, ["/exit"], row_width=3)
    bot.send_message(message.chat.id, texts.choose_sorting, reply_markup=markup)
    
    bot.set_state(message.from_user.id, states.ShowWordsState.show_words, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["vocabulary"] = vocab
        data["original_command"] = message.text


def process_choose_word_exit(message: Message, bot: TeleBot):
    bot.delete_state(message.from_user.id, message.chat.id)
    bot.reply_to(message, texts.exited)

    
def process_choose_word_sort(message: Message, bot: TeleBot):
    # (message, words, original_command):

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        if message.text not in options.show_words_sort_options:
            bot.reply_to(message, texts.sorting_not_supported.format(data["original_command"]))
            bot.delete_state(message.from_user.id, message.chat.id)
            return
        
        words = data["vocabulary"]
    
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


# def process_show_words_batch(message, words, batch_size, batch_number, original_command):
#     if batch_number != 0:
#         if message.text == "/exit":
#             bot.send_message(message.chat.id, texts.exited, reply_markup=empty_markup)
#             return
#         if message.text != "/next":
#             bot.send_message(message.chat.id, texts.unknown_command.format(original_command),
#                             reply_markup=empty_markup)
#             return
    
#     words_batch = words[batch_number * batch_size:(batch_number + 1) * batch_size]
#     words_formatted = [format_word_for_listing(word) for word in words_batch]
    
#     if len(words_batch) == 0:
#         bot.send_message(message.chat.id, texts.no_more_words, reply_markup=empty_markup)
#         return
    
#     n_pages = len(words) // batch_size
#     if len(words) % batch_size > 0:
#         n_pages += 1
        
#     markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=True)
#     markup.add(*["/exit", "/next"], row_width=2)
    
#     bot.send_message(
#         message.chat.id,
#         texts.word_formatted.format(batch_number + 1, n_pages, "\n".join(words_formatted)),
#         reply_markup=markup, parse_mode="MarkdownV2"
#     )
    
#     bot.register_next_step_handler(
#         message, CallbackLogger(process_show_words_batch),
#         words=words, batch_size=batch_size, batch_number=batch_number+1, original_command=original_command
#     )