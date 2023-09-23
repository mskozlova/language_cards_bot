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
