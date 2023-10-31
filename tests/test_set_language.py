import sys

import utils
from fixtures import chat_id, test_client

sys.path.append("../")
import user_interaction.texts as texts


def test_prepare(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/stop") as command:
        command.expect_next(texts.stop_message)

    with utils.CommandContext(test_client, chat_id, "/clear_db") as command:
        command.expect_next("Done!")


def test_set_language_cancel(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/set_language") as command:
        command.expect_next(texts.welcome)
        command.expect_next(texts.create_new_language)

    with utils.CommandContext(test_client, chat_id, "/cancel") as command:
        command.expect_next(texts.cancel_short)


def test_set_language_new(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/set_language") as command:
        command.expect_next(texts.create_new_language)

    with utils.CommandContext(test_client, chat_id, "fi") as command:
        command.expect_next(texts.create_translation_language)

    with utils.CommandContext(test_client, chat_id, "rus") as command:
        command.expect_next(texts.new_language_created.format("rus->fi"))
        command.expect_next(texts.language_is_set.format("rus->fi"))


def test_set_language_new_cancel(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/set_language") as command:
        command.expect_next(texts.current_language.format("rus->fi"))
        command.expect_next(texts.set_language)

    with utils.CommandContext(test_client, chat_id, "/cancel") as command:
        command.expect_next(texts.cancel_short)


def test_set_second_language(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/set_language") as command:
        command.expect_next(texts.current_language.format("rus->fi"))
        command.expect_next(texts.set_language)

    with utils.CommandContext(test_client, chat_id, "/new") as command:
        command.expect_next(texts.create_new_language)

    with utils.CommandContext(test_client, chat_id, "🇮🇩") as command:
        command.expect_next(texts.create_translation_language)

    with utils.CommandContext(test_client, chat_id, "🇷🇺") as command:
        command.expect_next(texts.new_language_created.format("🇷🇺->🇮🇩"))
        command.expect_next(texts.language_is_set.format("🇷🇺->🇮🇩"))


def test_set_switch_language(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/set_language") as command:
        command.expect_next(texts.current_language.format("🇷🇺->🇮🇩"))
        command.expect_next(texts.set_language)

    with utils.CommandContext(test_client, chat_id, "rus->fi") as command:
        command.expect_next(texts.language_is_set.format("rus->fi"))


def test_language_already_exists(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/set_language") as command:
        command.expect_next(texts.current_language.format("rus->fi"))
        command.expect_next(texts.set_language)

    with utils.CommandContext(test_client, chat_id, "/new") as command:
        command.expect_next(texts.create_new_language)

    with utils.CommandContext(test_client, chat_id, "🇮🇩") as command:
        command.expect_next(texts.create_translation_language)

    with utils.CommandContext(test_client, chat_id, "🇷🇺") as command:
        command.expect_next(texts.language_already_exists.format("🇷🇺->🇮🇩"))


def test_set_wrong_language_format(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/set_language") as command:
        command.expect_next(texts.current_language.format("rus->fi"))
        command.expect_next(texts.set_language)

    with utils.CommandContext(test_client, chat_id, "/new") as command:
        command.expect_next(texts.create_new_language)

    with utils.CommandContext(test_client, chat_id, "abc cba") as command:
        command.expect_next(texts.bad_language_format)

    with utils.CommandContext(test_client, chat_id, "abc123") as command:
        command.expect_next(texts.bad_language_format)

    with utils.CommandContext(test_client, chat_id, "🐍") as command:
        command.expect_next(texts.bad_language_format)

    with utils.CommandContext(test_client, chat_id, "😄") as command:
        command.expect_next(texts.bad_language_format)

    with utils.CommandContext(test_client, chat_id, "🏴󠁧󠁢󠁳󠁣󠁴󠁿") as command:
        command.expect_next(texts.create_translation_language)

    with utils.CommandContext(test_client, chat_id, "/cancel") as command:
        command.expect_next(texts.cancel_short)
