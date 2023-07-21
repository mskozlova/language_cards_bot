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


def test_set_language_new(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/set_language") as command:
        command.expect_next(texts.no_languages_yet)
    
    with utils.CommandContext(test_client, chat_id, "en") as command:
        command.expect_next(texts.welcome)
        command.expect_next(texts.new_language_created.format("en"))
        command.expect_next(texts.language_is_set.format("en"))


def test_set_language_cancel(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/set_language") as command:
        command.expect_next(texts.current_language.format("en"))
        command.expect_next(texts.set_language)
     
    with utils.CommandContext(test_client, chat_id, "/cancel") as command:
        command.expect_next(texts.set_language_cancel)


def test_set_second_language(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/set_language") as command:
        command.expect_next(texts.current_language.format("en"))
        command.expect_next(texts.set_language)
    
    with utils.CommandContext(test_client, chat_id, "fi") as command:
        command.expect_next(texts.new_language_created.format("fi"))
        command.expect_next(texts.language_is_set.format("fi"))


def test_set_switch_language(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/set_language") as command:
        command.expect_next(texts.current_language.format("fi"))
        command.expect_next(texts.set_language)
    
    with utils.CommandContext(test_client, chat_id, "en") as command:
        command.expect_next(texts.language_is_set.format("en"))
