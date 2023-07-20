from client import client
from logs import logger
import test_cases


test_chat_id = "@language_cards_tester_bot"

client.start()

test_cases.test_stop(client, test_chat_id, logger)
test_cases.test_clear_db(client, test_chat_id, logger)
test_cases.test_start(client, test_chat_id, logger)
test_cases.test_help(client, test_chat_id, logger)
test_cases.test_set_language(client, test_chat_id, logger)
test_cases.test_set_language_cancel(client, test_chat_id, logger)

client.stop()
