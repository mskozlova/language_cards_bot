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


def test_create_groups(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/create_group") as command:
        command.expect_any()

    with utils.CommandContext(test_client, chat_id, "abc") as command:
        command.expect_any()

    with utils.CommandContext(test_client, chat_id, "/create_group") as command:
        command.expect_any()

    with utils.CommandContext(test_client, chat_id, "cba") as command:
        command.expect_any()


def test_delete_group_exit(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/delete_group") as command:
        command.expect_next(texts.group_choose)

    with utils.CommandContext(test_client, chat_id, "/exit") as command:
        command.expect_next(texts.exited)


def test_delete_group_cancel(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/delete_group") as command:
        command.expect_next(texts.group_choose)

    with utils.CommandContext(test_client, chat_id, "abc") as command:
        command.expect_next(texts.delete_group_warning.format("abc", "rus->fi"))

    with utils.CommandContext(test_client, chat_id, "No..") as command:
        command.expect_next(texts.delete_group_cancel)


def test_delete_group(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/delete_group") as command:
        command.expect_next(texts.group_choose)

    with utils.CommandContext(test_client, chat_id, "abc") as command:
        command.expect_next(texts.delete_group_warning.format("abc", "rus->fi"))

    with utils.CommandContext(test_client, chat_id, "Yes!") as command:
        command.expect_next(texts.delete_group_success.format("abc"))

    with utils.CommandContext(test_client, chat_id, "/show_groups") as command:
        command.expect_any()

    with utils.CommandContext(test_client, chat_id, "abc") as command:
        command.expect_next(texts.no_such_group)

    with utils.CommandContext(test_client, chat_id, "/exit") as command:
        command.expect_any()


def test_delete_group_nonexistent(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/delete_group") as command:
        command.expect_next(texts.group_choose)

    with utils.CommandContext(test_client, chat_id, "gjgjgjgjg") as command:
        command.expect_next(texts.no_such_group)
        command.expect_next(texts.group_choose)

    with utils.CommandContext(test_client, chat_id, "/exit") as command:
        command.expect_any()
