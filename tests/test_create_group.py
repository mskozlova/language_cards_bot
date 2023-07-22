import sys

from fixtures import chat_id, test_client
import utils

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


def test_create_group(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/create_group") as command:
        command.expect_next(texts.create_group_name)
    
    with utils.CommandContext(test_client, chat_id, "abc") as command:
        command.expect_next(texts.group_created)


def test_create_group_same_name(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/create_group") as command:
        command.expect_next(texts.create_group_name)
    
    with utils.CommandContext(test_client, chat_id, "abc") as command:
        command.expect_next(texts.group_already_exists)


def test_create_group_cancel(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/create_group") as command:
        command.expect_next(texts.create_group_name)
    
    with utils.CommandContext(test_client, chat_id, "/cancel") as command:
        command.expect_next(texts.cancel_short)
