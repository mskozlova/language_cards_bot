import json

from telebot import TeleBot
from telebot.types import Message

import database.model as db_model
from database.ydb_settings import pool
from logs import logger, logged_execution
import user_interaction.options as options
import user_interaction.texts as texts

import bot.keyboards as keyboards
import bot.states as states


@logged_execution
def handle_help(message: Message, bot: TeleBot):
    m = bot.send_message(message.chat.id, texts.help_message)
    logger.warning(f"bot id: {m.from_user.id}")


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
        handle_language_not_set(message)
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
            translation_message = bot.send_message(
                message.chat.id, data["words"][len(data["translations"])]
            )
