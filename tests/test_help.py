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


def test_start(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/start") as command:
        command.expect_next_prefix("Ahoy, sexy!")


def test_help(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/help") as command:
        command.expect_next_prefix("Ahoy, sexy!")

def test_howto(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/howto") as command:
        command.expect_next_prefix("How to start learning?")

def test_howto_training(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/howto_training") as command:
        command.expect_next_prefix("How to train")

def test_howto_groups(test_client, chat_id):
    with utils.CommandContext(test_client, chat_id, "/howto_groups") as command:
        command.expect_next_prefix("How to create and manage groups")
