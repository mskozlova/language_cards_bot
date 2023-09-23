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

    with utils.CommandContext(test_client, chat_id, "/set_language") as command:
        command.expect_any()

    with utils.CommandContext(test_client, chat_id, "en") as command:
        command.expect_any_multiple(3)


def test_show_words_empty(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/show_words") as command:
        command.expect_next(texts.no_words_yet)

    with utils.CommandContext(test_client, chat_id, "a-z") as command:
        command.expect_none()


def test_add_words(test_client, chat_id):
    words_to_add = list(map(str, range(10)))

    with utils.CommandContext(test_client, chat_id, "/add_words") as command:
        command.expect_any()

    with utils.CommandContext(test_client, chat_id, "\n".join(words_to_add)) as command:
        command.expect_any_multiple(2)

    for word in words_to_add:
        with utils.CommandContext(test_client, chat_id, word) as command:
            command.expect_any()


def test_show_words_1_page(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/show_words") as command:
        command.expect_next(texts.words_count.format(10, "en"))
        command.expect_next(texts.choose_sorting)

    with utils.CommandContext(test_client, chat_id, "a-z") as command:
        command.expect_next_prefix("Page 1 of 1:")

    with utils.CommandContext(test_client, chat_id, "/next") as command:
        command.expect_none()


def test_add_more_words(test_client, chat_id):
    words_to_add = list(map(str, range(10, 25)))

    with utils.CommandContext(test_client, chat_id, "/add_words") as command:
        command.expect_any()

    with utils.CommandContext(test_client, chat_id, "\n".join(words_to_add)) as command:
        command.expect_any_multiple(2)

    for word in words_to_add:
        with utils.CommandContext(test_client, chat_id, word) as command:
            command.expect_any()


def test_show_words_2_pages(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/show_words") as command:
        command.expect_next(texts.words_count.format(25, "en"))
        command.expect_next(texts.choose_sorting)

    with utils.CommandContext(test_client, chat_id, "a-z") as command:
        command.expect_next_prefix("Page 1 of 2:")

    with utils.CommandContext(test_client, chat_id, "/next") as command:
        command.expect_next_prefix("Page 2 of 2:")

    with utils.CommandContext(test_client, chat_id, "/next") as command:
        command.expect_none()


def test_show_words_2_pages_exit(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/show_words") as command:
        command.expect_next(texts.words_count.format(25, "en"))
        command.expect_next(texts.choose_sorting)

    with utils.CommandContext(test_client, chat_id, "a-z") as command:
        command.expect_next_prefix("Page 1 of 2:")

    with utils.CommandContext(test_client, chat_id, "/exit") as command:
        command.expect_next(texts.exited)

    with utils.CommandContext(test_client, chat_id, "/next") as command:
        command.expect_none()
