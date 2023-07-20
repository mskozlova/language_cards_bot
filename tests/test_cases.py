import os
import sys

from pyrogram import Client
import pytest

import utils

sys.path.append("../")
import user_interaction.texts as texts


api_id = os.environ.get("TELEGRAM_API_ID")
api_hash = os.environ.get("TELEGRAM_API_HASH")
client_name = "languagecardsbottester"
workdir = "/Users/mariakozlova/ml_and_staff/language_cards_bot/tests"


@pytest.fixture(scope="session")
def test_client():
    client = Client(client_name, api_id, api_hash, workdir=workdir)
    client.start()
    yield client
    client.stop()


@pytest.fixture(scope="session")
def chat_id():
    return "@language_cards_tester_bot"


def test_stop(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/stop") as command:
        command.expect_next(texts.stop_message)


def test_clear_db(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/clear_db") as command:
        command.expect_next("Done!")


def test_start(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/start") as command:
        command.expect_next_prefix("Ahoy, sexy!")


def test_help(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/help") as command:
        command.expect_next_prefix("Ahoy, sexy!")


def test_set_language(test_client, chat_id):
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
