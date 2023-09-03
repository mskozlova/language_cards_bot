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


# def test_prepare_group_add_words(test_client, chat_id):
    