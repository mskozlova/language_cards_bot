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
        command.expect_any_multiple(2)

    with utils.CommandContext(test_client, chat_id, "fi") as command:
        command.expect_any()

    with utils.CommandContext(test_client, chat_id, "rus") as command:
        command.expect_any_multiple(2)

    with utils.CommandContext(test_client, chat_id, "/create_group") as command:
        command.expect_any()

    with utils.CommandContext(test_client, chat_id, "abc") as command:
        command.expect_any()


def test_prepare_add_words(test_client, chat_id):
    words = list(map(str, range(12, 0, -2)))

    with utils.CommandContext(test_client, chat_id, "/add_words") as command:
        command.expect_any()

    with utils.CommandContext(test_client, chat_id, "one-by-one") as command:
        command.expect_any()

    with utils.CommandContext(test_client, chat_id, "\n".join(words)) as command:
        command.expect_any_multiple(2)

    for word in words:
        with utils.CommandContext(test_client, chat_id, word + "-1") as command:
            command.expect_any()


def test_group_add_words_az(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/group_add_words") as command:
        command.expect_next(texts.group_choose)

    with utils.CommandContext(test_client, chat_id, "abc") as command:
        command.expect_next(texts.choose_sorting)

    with utils.CommandContext(test_client, chat_id, "a-z") as command:
        command.expect_next(texts.group_edit_choose.format("add", "abc", 1, 1))

    with utils.CommandContext(test_client, chat_id, "🖤10-1 - 10") as command:
        command.expect_next(texts.group_edit_confirm)

    with utils.CommandContext(test_client, chat_id, "💚10-1 - 10") as command:
        command.expect_next(texts.group_edit_confirm)

    with utils.CommandContext(test_client, chat_id, "🖤2-1 - 2") as command:
        command.expect_next(texts.group_edit_confirm)

    with utils.CommandContext(test_client, chat_id, "🖤4-1 - 4") as command:
        command.expect_next(texts.group_edit_confirm)

    with utils.CommandContext(test_client, chat_id, "🖤5-1 - 5") as command:
        command.expect_next(texts.group_edit_unknown_word)

    with utils.CommandContext(test_client, chat_id, "/exit") as command:
        command.expect_next_prefix(
            texts.group_edit_finished[:40].format("abc", "add", "2")
        )


def test_prepare_add_more_words(test_client, chat_id):
    words = list(map(str, range(13, 1, -2)))

    with utils.CommandContext(test_client, chat_id, "/add_words") as command:
        command.expect_any()

    with utils.CommandContext(test_client, chat_id, "one-by-one") as command:
        command.expect_any()

    with utils.CommandContext(test_client, chat_id, "\n".join(words)) as command:
        command.expect_any_multiple(2)

    for word in words:
        with utils.CommandContext(test_client, chat_id, word + "-1") as command:
            command.expect_any()


def test_group_add_words_az_1(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/group_add_words") as command:
        command.expect_next(texts.group_choose)

    with utils.CommandContext(test_client, chat_id, "abc") as command:
        command.expect_next(texts.choose_sorting)

    with utils.CommandContext(test_client, chat_id, "a-z") as command:
        command.expect_next(texts.group_edit_choose.format("add", "abc", 1, 2))

    with utils.CommandContext(test_client, chat_id, "🖤10-1 - 10") as command:
        command.expect_next(texts.group_edit_confirm)

    with utils.CommandContext(test_client, chat_id, "🖤13-1 - 13") as command:
        command.expect_next(texts.group_edit_confirm)

    with utils.CommandContext(test_client, chat_id, "💚13-1 - 13") as command:
        command.expect_next(texts.group_edit_confirm)

    with utils.CommandContext(test_client, chat_id, "🖤6-1 - 6") as command:
        command.expect_next(texts.group_edit_unknown_word)

    with utils.CommandContext(test_client, chat_id, "/next") as command:
        command.expect_next(texts.group_edit_choose.format("add", "abc", 2, 2))

    with utils.CommandContext(test_client, chat_id, "🖤6-1 - 6") as command:
        command.expect_next(texts.group_edit_confirm)

    with utils.CommandContext(test_client, chat_id, "🖤9-1 - 9") as command:
        command.expect_next(texts.group_edit_confirm)

    with utils.CommandContext(test_client, chat_id, "💚9-1 - 9") as command:
        command.expect_next(texts.group_edit_confirm)

    with utils.CommandContext(test_client, chat_id, "/exit") as command:
        command.expect_next_prefix(
            texts.group_edit_finished[:40].format("abc", "add", 2)
        )


def test_group_add_words_time_added(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/group_add_words") as command:
        command.expect_next(texts.group_choose)

    with utils.CommandContext(test_client, chat_id, "abc") as command:
        command.expect_next(texts.choose_sorting)

    with utils.CommandContext(test_client, chat_id, "time added ⬇️") as command:
        command.expect_next(texts.group_edit_choose.format("add", "abc", 1, 2))

    with utils.CommandContext(test_client, chat_id, "🖤9-1 - 9") as command:
        command.expect_next(texts.group_edit_confirm)

    with utils.CommandContext(test_client, chat_id, "🖤13-1 - 13") as command:
        command.expect_next(texts.group_edit_confirm)

    with utils.CommandContext(test_client, chat_id, "💚13-1 - 13") as command:
        command.expect_next(texts.group_edit_confirm)

    with utils.CommandContext(test_client, chat_id, "🖤12-1 - 12") as command:
        command.expect_next(texts.group_edit_unknown_word)

    with utils.CommandContext(test_client, chat_id, "/next") as command:
        command.expect_next(texts.group_edit_choose.format("add", "abc", 2, 2))

    with utils.CommandContext(test_client, chat_id, "🖤12-1 - 12") as command:
        command.expect_next(texts.group_edit_confirm)

    with utils.CommandContext(test_client, chat_id, "🖤13-1 - 13") as command:
        command.expect_next(texts.group_edit_unknown_word)

    with utils.CommandContext(test_client, chat_id, "/exit") as command:
        command.expect_next_prefix(
            texts.group_edit_finished[:40].format("abc", "add", 2)
        )


def test_group_add_words_exit(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/group_add_words") as command:
        command.expect_next(texts.group_choose)

    with utils.CommandContext(test_client, chat_id, "/exit") as command:
        command.expect_next(texts.exited)


def test_group_add_words_exit_sorting(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/group_add_words") as command:
        command.expect_next(texts.group_choose)

    with utils.CommandContext(test_client, chat_id, "abc") as command:
        command.expect_next(texts.choose_sorting)

    with utils.CommandContext(test_client, chat_id, "/exit") as command:
        command.expect_next(texts.exited)


def test_group_add_words_cancel_first_page(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/group_add_words") as command:
        command.expect_next(texts.group_choose)

    with utils.CommandContext(test_client, chat_id, "abc") as command:
        command.expect_next(texts.choose_sorting)

    with utils.CommandContext(test_client, chat_id, "time added ⬇️") as command:
        command.expect_next(texts.group_edit_choose.format("add", "abc", 1, 1))

    with utils.CommandContext(test_client, chat_id, "/cancel") as command:
        command.expect_next(texts.cancel_short)


def test_group_add_words_cancel_second_page(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/group_add_words") as command:
        command.expect_next(texts.group_choose)

    with utils.CommandContext(test_client, chat_id, "abc") as command:
        command.expect_next(texts.choose_sorting)

    with utils.CommandContext(test_client, chat_id, "time added ⬇️") as command:
        command.expect_next(texts.group_edit_choose.format("add", "abc", 1, 1))

    with utils.CommandContext(test_client, chat_id, "🖤13-1 - 13") as command:
        command.expect_next(texts.group_edit_confirm)

    with utils.CommandContext(test_client, chat_id, "/cancel") as command:
        command.expect_next(texts.cancel_short)
