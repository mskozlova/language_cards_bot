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


def test_show_empty_group(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/create_group") as command:
        command.expect_any()

    with utils.CommandContext(test_client, chat_id, "abc") as command:
        command.expect_any()

    with utils.CommandContext(test_client, chat_id, "/show_groups") as command:
        command.expect_next(texts.group_choose)

    with utils.CommandContext(test_client, chat_id, "abc") as command:
        command.expect_next(texts.show_group_empty)


def test_show_nonexistent_group(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/show_groups") as command:
        command.expect_next(texts.group_choose)

    with utils.CommandContext(test_client, chat_id, "bca") as command:
        command.expect_next(texts.no_such_group)

    with utils.CommandContext(test_client, chat_id, "abc") as command:
        command.expect_next(texts.show_group_empty)


def test_prepare_add_words(test_client, chat_id):
    words = list(map(str, range(10)))

    with utils.CommandContext(test_client, chat_id, "/add_words") as command:
        command.expect_next(texts.add_words_choose_mode)

    with utils.CommandContext(test_client, chat_id, "one-by-one") as command:
        command.expect_next(texts.add_words_instruction_one_by_one_1)

    with utils.CommandContext(test_client, chat_id, "\n".join(words)) as command:
        command.expect_any_multiple(2)

    for word in words:
        with utils.CommandContext(test_client, chat_id, word + "-1") as command:
            command.expect_any()

    with utils.CommandContext(test_client, chat_id, "/group_add_words") as command:
        command.expect_any()

    with utils.CommandContext(test_client, chat_id, "abc") as command:
        command.expect_any()

    with utils.CommandContext(test_client, chat_id, "a-z") as command:
        command.expect_any()

    for word in words[:6]:
        with utils.CommandContext(
            test_client, chat_id, f"🖤{word}-1 - {word}"
        ) as command:
            command.expect_any()

    with utils.CommandContext(test_client, chat_id, "/next") as command:
        command.expect_any()

    for word in words[6:]:
        with utils.CommandContext(
            test_client, chat_id, f"🖤{word}-1 - {word}"
        ) as command:
            command.expect_any()

    with utils.CommandContext(test_client, chat_id, "/exit") as command:
        command.expect_any()


def test_show_short_group(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/show_groups") as command:
        command.expect_next(texts.group_choose)

    with utils.CommandContext(test_client, chat_id, "abc") as command:
        command.expect_next_number_of_rows(10 + 3)

    with utils.CommandContext(test_client, chat_id, "/next") as command:
        command.expect_none()


def test_delete_words_from_group(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/group_delete_words") as command:
        command.expect_any()

    with utils.CommandContext(test_client, chat_id, "abc") as command:
        command.expect_any()

    with utils.CommandContext(test_client, chat_id, "a-z") as command:
        command.expect_any()

    with utils.CommandContext(test_client, chat_id, "💚0-1 - 0") as command:
        command.expect_any()

    with utils.CommandContext(test_client, chat_id, "/exit") as command:
        command.expect_any()

    with utils.CommandContext(test_client, chat_id, "/show_groups") as command:
        command.expect_next(texts.group_choose)

    with utils.CommandContext(test_client, chat_id, "abc") as command:
        command.expect_next_number_of_rows(9 + 3)


def test_delete_words_from_vocabulary(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/delete_words") as command:
        command.expect_any()

    with utils.CommandContext(test_client, chat_id, "1\n2") as command:
        command.expect_any()

    with utils.CommandContext(test_client, chat_id, "/show_groups") as command:
        command.expect_next(texts.group_choose)

    with utils.CommandContext(test_client, chat_id, "abc") as command:
        command.expect_next_number_of_rows(7 + 3)


def test_prepare_add_more_words(test_client, chat_id):
    words = list(map(str, range(10, 30)))

    with utils.CommandContext(test_client, chat_id, "/add_words") as command:
        command.expect_next(texts.add_words_choose_mode)

    with utils.CommandContext(test_client, chat_id, "one-by-one") as command:
        command.expect_next(texts.add_words_instruction_one_by_one_1)

    with utils.CommandContext(test_client, chat_id, "\n".join(words)) as command:
        command.expect_any_multiple(2)

    for word in words:
        with utils.CommandContext(test_client, chat_id, word + "-1") as command:
            command.expect_any()

    with utils.CommandContext(test_client, chat_id, "/group_add_words") as command:
        command.expect_any()

    with utils.CommandContext(test_client, chat_id, "abc") as command:
        command.expect_any()

    with utils.CommandContext(test_client, chat_id, "a-z") as command:
        command.expect_any()

    for word in words[:5]:
        with utils.CommandContext(
            test_client, chat_id, f"🖤{word}-1 - {word}"
        ) as command:
            command.expect_any()

    with utils.CommandContext(test_client, chat_id, "/next") as command:
        command.expect_any()

    for word in words[5:11]:
        with utils.CommandContext(
            test_client, chat_id, f"🖤{word}-1 - {word}"
        ) as command:
            command.expect_any()

    with utils.CommandContext(test_client, chat_id, "/next") as command:
        command.expect_any()

    for word in words[11:17]:
        with utils.CommandContext(
            test_client, chat_id, f"🖤{word}-1 - {word}"
        ) as command:
            command.expect_any()

    with utils.CommandContext(test_client, chat_id, "/next") as command:
        command.expect_any()

    for word in words[17:23]:
        with utils.CommandContext(
            test_client, chat_id, f"🖤{word}-1 - {word}"
        ) as command:
            command.expect_any()

    with utils.CommandContext(test_client, chat_id, "/next") as command:
        command.expect_any()

    for word in words[23:]:
        with utils.CommandContext(
            test_client, chat_id, f"🖤{word}-1 - {word}"
        ) as command:
            command.expect_any()

    with utils.CommandContext(test_client, chat_id, "/exit") as command:
        command.expect_any()


def test_show_long_group(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/show_groups") as command:
        command.expect_next(texts.group_choose)

    with utils.CommandContext(test_client, chat_id, "abc") as command:
        command.expect_next_number_of_rows(20 + 3)

    with utils.CommandContext(test_client, chat_id, "/next") as command:
        command.expect_next_number_of_rows(7 + 3)


def test_exit(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/show_groups") as command:
        command.expect_next(texts.group_choose)

    with utils.CommandContext(test_client, chat_id, "/exit") as command:
        command.expect_next(texts.exited)

    with utils.CommandContext(test_client, chat_id, "abc") as command:
        command.expect_none()
