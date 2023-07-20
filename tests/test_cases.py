import sys

import utils

sys.path.append("../")
import user_interaction.texts as texts


def test_stop(client, chat_id, logger):
    with utils.CommandContext(client, chat_id, "/stop", logger) as command:
        command.expect_next(texts.stop_message)


def test_clear_db(client, chat_id, logger):
    with utils.CommandContext(client, chat_id, "/clear_db", logger) as command:
        command.expect_next("Done!")


def test_start(client, chat_id, logger):
    with utils.CommandContext(client, chat_id, "/start", logger) as command:
        command.expect_next_prefix("Ahoy, sexy!")


def test_help(client, chat_id, logger):
    with utils.CommandContext(client, chat_id, "/help", logger) as command:
        command.expect_next_prefix("Ahoy, sexy!")


def test_set_language(client, chat_id, logger):
    with utils.CommandContext(client, chat_id, "/set_language", logger) as command:
        command.expect_next(texts.no_languages_yet)
    
    with utils.CommandContext(client, chat_id, "en", logger) as command:
        command.expect_next(texts.welcome)
        command.expect_next(texts.new_language_created.format("en"))
        command.expect_next(texts.language_is_set.format("en"))


def test_set_language_cancel(client, chat_id, logger):
    with utils.CommandContext(client, chat_id, "/set_language", logger) as command:
        command.expect_next(texts.current_language.format("en"))
        command.expect_next(texts.set_language)
     
    with utils.CommandContext(client, chat_id, "/cancel", logger) as command:
        command.expect_next(texts.set_language_cancel)
