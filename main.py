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
import tests.handlers as test_handlers
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

bot.register_message_handler(handlers.handle_stop, state="*", commands=["stop"], pass_bot=True)

bot.register_message_handler(handlers.handle_help, commands=["help", "start"], pass_bot=True)

bot.register_message_handler(handlers.handle_forget_me, commands=["forget_me"], pass_bot=True)
bot.register_message_handler(handlers.process_forget_me, state=bot_states.ForgetMeState.init, pass_bot=True)

bot.register_message_handler(handlers.handle_set_language, commands=["set_language"], pass_bot=True)
bot.register_message_handler(handlers.process_cancel, commands=["cancel"],
                             state=bot_states.SetLanguageState.init, pass_bot=True)
bot.register_message_handler(handlers.process_setting_language,
                             state=bot_states.SetLanguageState.init, pass_bot=True)

bot.register_message_handler(handlers.handle_add_words, commands=["add_words"], pass_bot=True)
bot.register_message_handler(handlers.process_adding_words, state=bot_states.AddWordsState.add_words, pass_bot=True)
bot.register_message_handler(handlers.process_word_translation_stop, commands=["cancel"],
                             state=bot_states.AddWordsState.translate, pass_bot=True)
bot.register_message_handler(handlers.process_word_translation,
                             state=bot_states.AddWordsState.translate, pass_bot=True)

bot.register_message_handler(handlers.handle_show_words, commands=["show_words"], pass_bot=True)
bot.register_message_handler(handlers.process_exit,
                             state=bot_states.ShowWordsState.choose_sort,
                             commands=["exit"], pass_bot=True)
bot.register_message_handler(handlers.process_choose_word_sort, state=bot_states.ShowWordsState.choose_sort, pass_bot=True)
bot.register_message_handler(handlers.process_exit,
                             state=bot_states.ShowWordsState.show_words,
                             commands=["exit"], pass_bot=True)
bot.register_message_handler(handlers.process_show_words_batch_next,
                             state=bot_states.ShowWordsState.show_words,
                             commands=["next"], pass_bot=True)
bot.register_message_handler(handlers.process_show_words_batch_unknown,
                             state=bot_states.ShowWordsState.show_words,
                             pass_bot=True)

bot.register_message_handler(handlers.handle_show_current_language, commands=["show_current_language"], pass_bot=True)
bot.register_message_handler(handlers.handle_show_languages, commands=["show_languages"], pass_bot=True)

bot.register_message_handler(handlers.handle_delete_language, commands=["delete_language"], pass_bot=True)
bot.register_message_handler(handlers.process_delete_language,
                             state=bot_states.DeleteLanguageState.init, pass_bot=True)

bot.register_message_handler(handlers.handle_delete_words, commands=["delete_words"], pass_bot=True)
bot.register_message_handler(handlers.process_cancel,
                             state=bot_states.DeleteWordsState.init,
                             commands=["cancel"], pass_bot=True)
bot.register_message_handler(handlers.process_deleting_words,
                             state=bot_states.DeleteWordsState.init,
                             pass_bot=True)

bot.register_message_handler(handlers.handle_create_group, commands=["create_group"], pass_bot=True)
bot.register_message_handler(handlers.process_cancel,
                             commands=["cancel"],
                             state=bot_states.CreateGroupState.init,
                             pass_bot=True)
bot.register_message_handler(handlers.process_group_creation,
                             state=bot_states.CreateGroupState.init,
                             pass_bot=True)

bot.register_message_handler(handlers.handle_delete_group, commands=["delete_group"], pass_bot=True)
bot.register_message_handler(handlers.process_exit,
                             commands=["exit"],
                             state=bot_states.DeleteGroupState.select_group,
                             pass_bot=True)
bot.register_message_handler(handlers.process_group_deletion_check_sure,
                             state=bot_states.DeleteGroupState.select_group,
                             pass_bot=True)
bot.register_message_handler(handlers.process_group_deletion,
                             state=bot_states.DeleteGroupState.are_you_sure,
                             pass_bot=True)

bot.register_message_handler(handlers.handle_show_groups, commands=["show_groups"], pass_bot=True)
bot.register_message_handler(handlers.process_exit, commands=["exit"], state=bot_states.ShowGroupsState.init, pass_bot=True)
bot.register_message_handler(handlers.process_show_group_contents, state=bot_states.ShowGroupsState.init, pass_bot=True)

bot.register_message_handler(handlers.handle_group_add_words, commands=["group_add_words"], pass_bot=True)
bot.register_message_handler(handlers.process_exit, commands=["exit"], state=bot_states.AddGroupWordsState.choose_group, pass_bot=True)
bot.register_message_handler(handlers.handle_choose_group_to_add_words, state=bot_states.AddGroupWordsState.choose_group, pass_bot=True)
bot.register_message_handler(handlers.process_exit, commands=["exit"], state=bot_states.AddGroupWordsState.choose_sorting, pass_bot=True)
bot.register_message_handler(handlers.process_choose_sorting_to_add_words, state=bot_states.AddGroupWordsState.choose_sorting, pass_bot=True)
bot.register_message_handler(handlers.process_cancel, commands=["cancel"], state=bot_states.AddGroupWordsState.choose_words, pass_bot=True)
bot.register_message_handler(handlers.process_save_group_edit, commands=["exit"], state=bot_states.AddGroupWordsState.choose_words, pass_bot=True)
bot.register_message_handler(handlers.process_choose_words_batch_for_group_next, commands=["next"], state=bot_states.AddGroupWordsState.choose_words, pass_bot=True)
bot.register_message_handler(handlers.process_choose_words_batch_for_group, state=bot_states.AddGroupWordsState.choose_words, pass_bot=True)

# TODO: get rid of testing commands!
if os.getenv("IS_TESTING") is not None:
    bot.register_message_handler(test_handlers.handle_clear_db, commands=["clear_db"], pass_bot=True)

def handle_language_not_set(message, bot):
    bot.send_message(message.chat.id, texts.no_language_is_set)


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
