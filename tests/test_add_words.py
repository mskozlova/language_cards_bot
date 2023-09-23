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


def test_add_words(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/add_words") as command:
        command.expect_next(texts.add_words_instruction_1)

    with utils.CommandContext(test_client, chat_id, "a\nb\nc") as command:
        command.expect_next(texts.add_words_instruction_2.format(["a", "b", "c"]))
        command.expect_next(texts.add_words_translate.format("a"))

    with utils.CommandContext(test_client, chat_id, "a1") as command:
        command.expect_next("b")

    with utils.CommandContext(test_client, chat_id, "b1") as command:
        command.expect_next("c")

    with utils.CommandContext(test_client, chat_id, "c1") as command:
        command.expect_next(texts.add_words_finished.format(3))

    with utils.CommandContext(test_client, chat_id, "anything") as command:
        command.expect_none()


def test_add_words_cancel(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/add_words") as command:
        command.expect_next(texts.add_words_instruction_1)

    with utils.CommandContext(test_client, chat_id, "d\ne\nf") as command:
        command.expect_next(texts.add_words_instruction_2.format(["d", "e", "f"]))
        command.expect_next(texts.add_words_translate.format("d"))

    with utils.CommandContext(test_client, chat_id, "d1") as command:
        command.expect_next("e")

    with utils.CommandContext(test_client, chat_id, "/cancel") as command:
        command.expect_next(texts.add_words_cancelled)

    with utils.CommandContext(test_client, chat_id, "f1") as command:
        command.expect_none()
