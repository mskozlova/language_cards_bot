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


def test_show_current_language_empty(test_client, chat_id):
    with utils.CommandContext(
        test_client, chat_id, "/show_current_language"
    ) as command:
        command.expect_next(texts.no_language_is_set)


def test_set_first_language(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/set_language") as command:
        command.expect_any()

    with utils.CommandContext(test_client, chat_id, "en") as command:
        command.expect_any_multiple(3)

    with utils.CommandContext(
        test_client, chat_id, "/show_current_language"
    ) as command:
        command.expect_next(texts.current_language.format("en"))


def test_set_second_language(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/set_language") as command:
        command.expect_any_multiple(2)

    with utils.CommandContext(test_client, chat_id, "fi") as command:
        command.expect_any_multiple(2)

    with utils.CommandContext(
        test_client, chat_id, "/show_current_language"
    ) as command:
        command.expect_next(texts.current_language.format("fi"))


def test_delete_language(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/delete_language") as command:
        command.expect_any()

    with utils.CommandContext(test_client, chat_id, "Yes!") as command:
        command.expect_any()

    with utils.CommandContext(
        test_client, chat_id, "/show_current_language"
    ) as command:
        command.expect_next(texts.no_language_is_set)
