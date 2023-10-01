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


def test_add_words_one_by_one(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/add_words") as command:
        command.expect_next(texts.add_words_choose_mode)

    with utils.CommandContext(test_client, chat_id, "one-by-one") as command:
        command.expect_next(texts.add_words_instruction_one_by_one_1)

    with utils.CommandContext(test_client, chat_id, "a\nb\nc") as command:
        command.expect_next(texts.add_words_instruction_one_by_one_2.format(3))
        command.expect_next(texts.add_words_translate.format("a"))

    with utils.CommandContext(test_client, chat_id, "a1") as command:
        command.expect_next("b")

    with utils.CommandContext(test_client, chat_id, "b1") as command:
        command.expect_next("c")

    with utils.CommandContext(test_client, chat_id, "c1") as command:
        command.expect_next(texts.add_words_finished.format(3))

    with utils.CommandContext(test_client, chat_id, "anything") as command:
        command.expect_none()


def test_add_words_cancel_one_by_one(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/add_words") as command:
        command.expect_next(texts.add_words_choose_mode)

    with utils.CommandContext(test_client, chat_id, "one-by-one") as command:
        command.expect_next(texts.add_words_instruction_one_by_one_1)

    with utils.CommandContext(test_client, chat_id, "d\ne\nf") as command:
        command.expect_next(texts.add_words_instruction_one_by_one_2.format(3))
        command.expect_next(texts.add_words_translate.format("d"))

    with utils.CommandContext(test_client, chat_id, "d1") as command:
        command.expect_next("e")

    with utils.CommandContext(test_client, chat_id, "/cancel") as command:
        command.expect_next(texts.add_words_cancelled)

    with utils.CommandContext(test_client, chat_id, "f1") as command:
        command.expect_none()


def test_add_words_cancel_choose_mode(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/add_words") as command:
        command.expect_next(texts.add_words_choose_mode)

    with utils.CommandContext(test_client, chat_id, "/cancel") as command:
        command.expect_next(texts.cancel_short)


def test_add_words_cancel_one_by_one_add(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/add_words") as command:
        command.expect_next(texts.add_words_choose_mode)

    with utils.CommandContext(test_client, chat_id, "one-by-one") as command:
        command.expect_next(texts.add_words_instruction_one_by_one_1)

    with utils.CommandContext(test_client, chat_id, "/cancel") as command:
        command.expect_next(texts.cancel_short)


def test_add_words_cancel_together_add(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/add_words") as command:
        command.expect_next(texts.add_words_choose_mode)

    with utils.CommandContext(test_client, chat_id, "together") as command:
        command.expect_next(texts.add_words_together_instruction)

    with utils.CommandContext(test_client, chat_id, "/cancel") as command:
        command.expect_next(texts.cancel_short)


def test_add_words_together(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/add_words") as command:
        command.expect_next(texts.add_words_choose_mode)

    with utils.CommandContext(test_client, chat_id, "together") as command:
        command.expect_next(texts.add_words_together_instruction)

    words = """a = a1/ a2
    b = b1
    c = c1/c2 / c3
    """
    with utils.CommandContext(test_client, chat_id, words) as command:
        command.expect_next(texts.add_words_finished.format(3))


def test_add_words_together_wrong_format(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/add_words") as command:
        command.expect_next(texts.add_words_choose_mode)

    with utils.CommandContext(test_client, chat_id, "together") as command:
        command.expect_next(texts.add_words_together_instruction)

    with utils.CommandContext(test_client, chat_id, "a = a1/ a2\nb=") as command:
        command.expect_next(texts.add_words_together_empty_translation.format("b="))

    with utils.CommandContext(test_client, chat_id, "a = a1/ a2=\nb=") as command:
        command.expect_next(texts.add_words_together_wrong_format.format("a = a1/ a2="))

    with utils.CommandContext(
        test_client, chat_id, "a = a1/ a2\nb=b1\n    \t=c2/c3"
    ) as command:
        command.expect_next(texts.add_words_together_empty_word.format("=c2/c3"))

    with utils.CommandContext(
        test_client, chat_id, "a = a1/ a2\nb=b1\n    \tc=c2/c3"
    ) as command:
        command.expect_next(texts.add_words_finished.format(3))
