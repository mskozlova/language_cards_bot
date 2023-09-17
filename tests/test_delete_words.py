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


def test_add_words(test_client, chat_id):
    words = list(map(str, range(10)))
    
    with utils.CommandContext(test_client, chat_id, "/add_words") as command:
        command.expect_next(texts.add_words_instruction_1)
    
    with utils.CommandContext(test_client, chat_id, "\n".join(words)) as command:
        command.expect_next(texts.add_words_instruction_2.format(words))
        command.expect_any()
    
    for word in words:
        with utils.CommandContext(test_client, chat_id, word) as command:
            command.expect_any()


def test_delete_words(test_client, chat_id):
    words_to_delete = ["3", "5", "11"]
    
    with utils.CommandContext(test_client, chat_id, "/delete_words") as command:
        command.expect_next(texts.delete_words_start)
    
    with utils.CommandContext(test_client, chat_id, "\n".join(words_to_delete)) as command:
        command.expect_next_prefix("Deleted {} word(s)".format(2))
    
    with utils.CommandContext(test_client, chat_id, "/show_words") as command:
        command.expect_next_prefix("You have 8 word(s) for language")
        command.expect_next_prefix(texts.choose_sorting)

    with utils.CommandContext(test_client, chat_id, "/exit") as command:
        command.expect_any()
