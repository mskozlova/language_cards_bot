from functools import partial
import os

from telebot import TeleBot, custom_filters

from bot import handlers as handlers
from bot import states as bot_states

import tests.handlers as test_handlers


class Handler:
    def __init__(self, callback, **kwargs):
        self.callback = callback
        self.kwargs = kwargs


def get_start_handlers():
    return [
        Handler(handlers.handle_help, commands=["help", "start"]),
    ]


def get_forget_me_handlers():
    return [
        Handler(handlers.handle_forget_me, commands=["forget_me"]),
        Handler(handlers.process_forget_me, state=bot_states.ForgetMeState.init),
    ]


def get_set_language_handlers():
    return [
        Handler(handlers.handle_set_language, commands=["set_language"]),
        Handler(handlers.process_cancel, commands=["cancel"], state=bot_states.SetLanguageState.init),
        Handler(handlers.process_setting_language, state=bot_states.SetLanguageState.init),
    ]


def get_add_words_handlers():
    return [
        Handler(handlers.handle_add_words, commands=["add_words"]),
        Handler(
            handlers.process_adding_words, state=bot_states.AddWordsState.add_words,
        ),
        Handler(handlers.process_word_translation_stop, commands=["cancel"], state=bot_states.AddWordsState.translate),
        Handler(handlers.process_word_translation, state=bot_states.AddWordsState.translate),
    ]


def get_show_words_handlers():
    return [
        Handler(handlers.handle_show_words, commands=["show_words"]),
        Handler(handlers.process_exit, state=bot_states.ShowWordsState.choose_sort, commands=["exit"]),
        Handler(handlers.process_choose_word_sort, state=bot_states.ShowWordsState.choose_sort),
        Handler(handlers.process_exit, state=bot_states.ShowWordsState.show_words, commands=["exit"]),
        Handler(handlers.process_show_words_batch_next, state=bot_states.ShowWordsState.show_words, commands=["next"]),
        Handler(handlers.process_show_words_batch_unknown, state=bot_states.ShowWordsState.show_words),
    ]


def get_show_languages_handlers():
    return [
        Handler(handlers.handle_show_current_language, commands=["show_current_language"]),
        Handler(handlers.handle_show_languages, commands=["show_languages"]),
    ]


def get_delete_language_handlers():
    return [
        Handler(handlers.handle_delete_language, commands=["delete_language"]),
        Handler(handlers.process_delete_language, state=bot_states.DeleteLanguageState.init),
    ]


def get_delete_words_handlers():
    return [
        Handler(handlers.handle_delete_words, commands=["delete_words"]),
        Handler(handlers.process_cancel, state=bot_states.DeleteWordsState.init, commands=["cancel"]),
        Handler(handlers.process_deleting_words, state=bot_states.DeleteWordsState.init),
    ]


def get_create_group_handlers():
    return [
        Handler(handlers.handle_create_group, commands=["create_group"]),
        Handler(handlers.process_cancel, commands=["cancel"], state=bot_states.CreateGroupState.init),
        Handler(handlers.process_group_creation, state=bot_states.CreateGroupState.init),
    ]


def get_delete_group_handlers():
    return [
        Handler(handlers.handle_delete_group, commands=["delete_group"]),
        Handler(handlers.process_exit, commands=["exit"], state=bot_states.DeleteGroupState.select_group),
        Handler(handlers.process_group_deletion_check_sure, state=bot_states.DeleteGroupState.select_group),
        Handler(handlers.process_group_deletion, state=bot_states.DeleteGroupState.are_you_sure),
    ]


def get_show_groups_handlers():
    return [
        Handler(handlers.handle_show_groups, commands=["show_groups"]),
        Handler(handlers.process_exit, commands=["exit"], state=bot_states.DeleteGroupState.select_group),
        Handler(handlers.process_show_group_contents, state=bot_states.ShowGroupsState.init),
    ]


def get_group_add_words_handlers():
    return [
        Handler(handlers.handle_group_add_words, commands=["group_add_words"]),
        Handler(handlers.process_exit, commands=["exit"], state=bot_states.AddGroupWordsState.choose_group),
        Handler(handlers.handle_choose_group_to_add_words, state=bot_states.AddGroupWordsState.choose_group),
        Handler(handlers.process_exit, commands=["exit"], state=bot_states.AddGroupWordsState.choose_sorting),
        Handler(handlers.process_choose_sorting_to_add_words, state=bot_states.AddGroupWordsState.choose_sorting),
        Handler(handlers.process_cancel, commands=["cancel"], state=bot_states.AddGroupWordsState.choose_words),
        Handler(handlers.process_save_group_edit, commands=["exit"], state=bot_states.AddGroupWordsState.choose_words),
        Handler(handlers.process_choose_words_batch_for_group_next, commands=["next"], state=bot_states.AddGroupWordsState.choose_words),
        Handler(handlers.process_choose_words_batch_for_group, state=bot_states.AddGroupWordsState.choose_words),
    ]


def get_group_delete_words_handlers():
    return [
        Handler(handlers.handle_group_delete_words, commands=["group_delete_words"]),
        Handler(handlers.process_exit, commands=["exit"], state=bot_states.DeleteGroupWordsState.choose_group),
        Handler(handlers.handle_choose_group_to_delete_words, state=bot_states.DeleteGroupWordsState.choose_group),
        Handler(handlers.process_exit, commands=["exit"], state=bot_states.DeleteGroupWordsState.choose_sorting),
        Handler(handlers.process_choose_sorting_to_delete_words, state=bot_states.DeleteGroupWordsState.choose_sorting),
        Handler(handlers.process_cancel, commands=["cancel"], state=bot_states.DeleteGroupWordsState.choose_words),
        Handler(handlers.process_save_group_edit, commands=["exit"], state=bot_states.DeleteGroupWordsState.choose_words),
        Handler(handlers.process_choose_words_batch_for_group_next, commands=["next"], state=bot_states.DeleteGroupWordsState.choose_words),
        Handler(handlers.process_choose_words_batch_for_group, state=bot_states.DeleteGroupWordsState.choose_words),
    ]


def get_train_handlers():
    return [
        Handler(handlers.handle_train, commands=["train"]),
        Handler(handlers.process_cancel, commands=["cancel"], state=bot_states.TrainState.choose_strategy),
        Handler(handlers.process_choose_strategy, state=bot_states.TrainState.choose_strategy),
        Handler(handlers.process_exit, commands=["exit"], state=bot_states.TrainState.choose_group),
        Handler(handlers.process_choose_group_for_training, state=bot_states.TrainState.choose_group),
        Handler(handlers.process_cancel, commands=["cancel"], state=bot_states.TrainState.choose_direction),
        Handler(handlers.process_choose_direction, state=bot_states.TrainState.choose_direction),
        Handler(handlers.process_cancel, commands=["cancel"], state=bot_states.TrainState.choose_duration),
        Handler(handlers.process_choose_duration, state=bot_states.TrainState.choose_duration),
        Handler(handlers.process_cancel, commands=["cancel"], state=bot_states.TrainState.choose_hints),
        Handler(handlers.process_choose_hints, state=bot_states.TrainState.choose_hints),
        Handler(handlers.handle_train_step_stop, commands=["stop"], state=bot_states.TrainState.train),
        Handler(handlers.handle_train_step, state=bot_states.TrainState.train),
    ]


def get_test_handlers():
    return [
        Handler(test_handlers.handle_clear_db, commands=["clear_db"])
    ]


def get_stop_handler():
    return [
        Handler(handlers.handle_stop, state="*", commands=["stop"]),
    ]


def get_unknown_handler():
    return [
        Handler(handlers.handle_unknown),
    ]


def create_bot(bot_token, pool):
    state_storage = bot_states.StateYDBStorage(pool)
    bot = TeleBot(bot_token, state_storage=state_storage)

    handlers = []
    
    if os.getenv("IS_TESTING") is not None:
        handlers.extend(get_test_handlers())
    
    handlers.extend(get_start_handlers())
    handlers.extend(get_forget_me_handlers())
    handlers.extend(get_set_language_handlers())
    handlers.extend(get_add_words_handlers())
    handlers.extend(get_show_words_handlers())
    handlers.extend(get_show_languages_handlers())
    handlers.extend(get_delete_language_handlers())
    handlers.extend(get_delete_words_handlers())
    handlers.extend(get_create_group_handlers())
    handlers.extend(get_delete_group_handlers())
    handlers.extend(get_show_groups_handlers())
    handlers.extend(get_group_add_words_handlers())
    handlers.extend(get_group_delete_words_handlers())
    handlers.extend(get_train_handlers())
    
    handlers.extend(get_stop_handler())
    handlers.extend(get_unknown_handler())

    for handler in handlers:
        bot.register_message_handler(
            partial(handler.callback, pool=pool), **handler.kwargs, pass_bot=True
        )

    bot.add_custom_filter(custom_filters.StateFilter(bot))
    return bot
