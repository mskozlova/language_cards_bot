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

bot.register_message_handler(handlers.handle_group_delete_words, commands=["group_delete_words"], pass_bot=True)
bot.register_message_handler(handlers.process_exit, commands=["exit"], state=bot_states.DeleteGroupWordsState.choose_group, pass_bot=True)
bot.register_message_handler(handlers.handle_choose_group_to_delete_words, state=bot_states.DeleteGroupWordsState.choose_group, pass_bot=True)
bot.register_message_handler(handlers.process_exit, commands=["exit"], state=bot_states.DeleteGroupWordsState.choose_sorting, pass_bot=True)
bot.register_message_handler(handlers.process_choose_sorting_to_delete_words, state=bot_states.DeleteGroupWordsState.choose_sorting, pass_bot=True)
bot.register_message_handler(handlers.process_cancel, commands=["cancel"], state=bot_states.DeleteGroupWordsState.choose_words, pass_bot=True)
bot.register_message_handler(handlers.process_save_group_edit, commands=["exit"], state=bot_states.DeleteGroupWordsState.choose_words, pass_bot=True)
bot.register_message_handler(handlers.process_choose_words_batch_for_group_next, commands=["next"], state=bot_states.DeleteGroupWordsState.choose_words, pass_bot=True)
bot.register_message_handler(handlers.process_choose_words_batch_for_group, state=bot_states.DeleteGroupWordsState.choose_words, pass_bot=True)

bot.register_message_handler(handlers.handle_train, commands=["train"], pass_bot=True)
bot.register_message_handler(handlers.process_cancel, commands=["cancel"], state=bot_states.TrainState.choose_strategy, pass_bot=True)
bot.register_message_handler(handlers.process_choose_strategy, state=bot_states.TrainState.choose_strategy, pass_bot=True)
bot.register_message_handler(handlers.process_exit, commands=["exit"], state=bot_states.TrainState.choose_group, pass_bot=True)
bot.register_message_handler(handlers.process_choose_group_for_training, state=bot_states.TrainState.choose_group, pass_bot=True)
bot.register_message_handler(handlers.process_cancel, commands=["cancel"], state=bot_states.TrainState.choose_direction, pass_bot=True)
bot.register_message_handler(handlers.process_choose_direction, state=bot_states.TrainState.choose_direction, pass_bot=True)
bot.register_message_handler(handlers.process_cancel, commands=["cancel"], state=bot_states.TrainState.choose_duration, pass_bot=True)
bot.register_message_handler(handlers.process_choose_duration, state=bot_states.TrainState.choose_duration, pass_bot=True)
bot.register_message_handler(handlers.process_cancel, commands=["cancel"], state=bot_states.TrainState.choose_hints, pass_bot=True)
bot.register_message_handler(handlers.process_choose_hints, state=bot_states.TrainState.choose_hints, pass_bot=True)
bot.register_message_handler(handlers.handle_train_step_stop, commands=["stop"], state=bot_states.TrainState.train, pass_bot=True)
bot.register_message_handler(handlers.handle_train_step, state=bot_states.TrainState.train, pass_bot=True)

# TODO: get rid of testing commands!
if os.getenv("IS_TESTING") is not None:
    bot.register_message_handler(test_handlers.handle_clear_db, commands=["clear_db"], pass_bot=True)

def handle_language_not_set(message, bot):
    bot.send_message(message.chat.id, texts.no_language_is_set)

bot.register_message_handler(handlers.handle_unknown, pass_bot=True)

bot.add_custom_filter(custom_filters.StateFilter(bot))
