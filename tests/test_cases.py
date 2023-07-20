import sys

from logs import logger, logged_test
import utils

sys.path.append("../")
import user_interaction.texts as texts


@logged_test
def test_stop(client, chat_id):
    with utils.CommandContext(client, chat_id, "/stop", logger) as command:
        command.expect_next(texts.stop_message)


@logged_test
def test_clear_db(client, chat_id):
    with utils.CommandContext(client, chat_id, "/clear_db", logger) as command:
        command.expect_next("Done!")


@logged_test
def test_start(client, chat_id):
    with utils.CommandContext(client, chat_id, "/start", logger) as command:
        command.expect_next_prefix("Ahoy, sexy!")


@logged_test
def test_help(client, chat_id):
    with utils.CommandContext(client, chat_id, "/help", logger) as command:
        command.expect_next_prefix("Ahoy, sexy!")


@logged_test
def test_set_language(client, chat_id):
    with utils.CommandContext(client, chat_id, "/set_language", logger) as command:
        command.expect_next(texts.no_languages_yet)
    
    with utils.CommandContext(client, chat_id, "en", logger) as command:
        command.expect_next(texts.welcome)
        command.expect_next(texts.new_language_created.format("en"))
        command.expect_next(texts.language_is_set.format("en"))


@logged_test
def test_set_language_cancel(client, chat_id):
    with utils.CommandContext(client, chat_id, "/set_language", logger) as command:
        command.expect_next(texts.current_language.format("en"))
        command.expect_next(texts.set_language)
     
    with utils.CommandContext(client, chat_id, "/cancel", logger) as command:
        command.expect_next(texts.set_language_cancel)


@logged_test
def test_add_words(client, chat_id):
    with utils.CommandContext(client, chat_id, "/add_words", logger) as command:
        command.expect_next(texts.add_words_instruction_1)
    
    with utils.CommandContext(client, chat_id, "a\nb\nc", logger) as command:
        command.expect_next(texts.add_words_instruction_2.format(["a", "b", "c"]))
        command.expect_next(texts.add_words_translate.format("a"))
    
    with utils.CommandContext(client, chat_id, "a1", logger) as command:
        command.expect_next("b")
    
    with utils.CommandContext(client, chat_id, "b1", logger) as command:
        command.expect_next("c")
        
    with utils.CommandContext(client, chat_id, "c1", logger) as command:
        command.expect_next(texts.add_words_finished.format(3))


@logged_test
def test_add_words_cancel(client, chat_id):
    with utils.CommandContext(client, chat_id, "/add_words", logger) as command:
        command.expect_next(texts.add_words_instruction_1)
    
    with utils.CommandContext(client, chat_id, "d\ne\nf", logger) as command:
        command.expect_next(texts.add_words_instruction_2.format(["d", "e", "f"]))
        command.expect_next(texts.add_words_translate.format("d"))
    
    with utils.CommandContext(client, chat_id, "d1", logger) as command:
        command.expect_next("e")
    
    with utils.CommandContext(client, chat_id, "/cancel", logger) as command:
        command.expect_next(texts.add_words_cancelled)
        
    with utils.CommandContext(client, chat_id, "f1", logger) as command:
        command.expect_none()
