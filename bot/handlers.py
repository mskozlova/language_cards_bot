from hashlib import blake2b
import json

import database.model as db_model
from database.ydb_settings import pool
from logs import logger, logged_execution
from user_interaction import options, texts
import word as word_utils

from bot import constants, keyboards, states, utils


# common
@logged_execution
def process_exit(message, bot):
    bot.delete_state(message.from_user.id, message.chat.id)
    bot.reply_to(message, texts.exited)


@logged_execution
def process_cancel(message, bot):
    bot.delete_state(message.from_user.id, message.chat.id)
    bot.send_message(message.chat.id, texts.cancel_short, reply_markup=keyboards.empty)


# TODO: add user to db after hitting /help or /start
@logged_execution
def handle_help(message, bot):
    bot.send_message(message.chat.id, texts.help_message, reply_markup=keyboards.empty)


@logged_execution
def handle_stop(message, bot):
    bot.delete_state(message.from_user.id, message.chat.id)
    bot.send_message(message.chat.id, texts.stop_message, reply_markup=keyboards.empty)


@logged_execution
def handle_forget_me(message, bot):
    markup = keyboards.get_reply_keyboard(options.delete_are_you_sure)
    bot.set_state(message.from_user.id, states.ForgetMeState.init, message.chat.id)
    bot.send_message(message.chat.id, texts.forget_me_warning, reply_markup=markup)


# forget me
@logged_execution
def process_forget_me(message, bot):
    bot.delete_state(message.from_user.id, message.chat.id)

    if message.text not in options.delete_are_you_sure:
        bot.reply_to(message, texts.unknown_command_short)
        return
    
    if options.delete_are_you_sure[message.text]:
        db_model.delete_user(pool, message.chat.id)
        bot.send_message(message.chat.id, texts.forget_me_final, reply_markup=keyboards.empty)
    else:
        bot.send_message(message.chat.id, texts.cancel_short, reply_markup=keyboards.empty)


@logged_execution
def handle_unknown(message, bot):
    # bot.reply_to(message, texts.unknown_message)
    logger.warning(f"Unknown message! chat_id: {message.chat.id}, message: {message.text}")


# set language

# TODO: check language name (same as group name)
@logged_execution
def handle_set_language(message, bot):
    language = db_model.get_current_language(pool, message.chat.id)
    if language is not None:
        bot.send_message(message.chat.id, texts.current_language.format(language), reply_markup=keyboards.empty)
    
    languages = db_model.get_available_languages(pool, message.chat.id)
    
    if len(languages) == 0:
        bot.send_message(message.chat.id, texts.no_languages_yet, reply_markup=keyboards.empty)
    else:
        markup = keyboards.get_reply_keyboard(languages, ["/cancel"])
        bot.send_message(message.chat.id, texts.set_language, reply_markup=markup)
    
    bot.set_state(message.from_user.id, states.SetLanguageState.init, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["languages"] = languages


@logged_execution
def process_setting_language(message, bot):
    language = message.text.lower().strip()
    user_info = db_model.get_user_info(pool, message.chat.id)
    
    if len(user_info) == 0: # new user!
        bot.send_message(message.chat.id, texts.welcome, reply_markup=keyboards.empty)
        db_model.create_user(pool, message.chat.id)
    
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        if language not in data["languages"]:
            bot.send_message(
                message.chat.id,
                texts.new_language_created.format(language),
                reply_markup=keyboards.empty
            )
            db_model.user_add_language(pool, message.chat.id, language)

    bot.delete_state(message.from_user.id, message.chat.id)

    db_model.update_current_lang(pool, message.chat.id, language)
    bot.send_message(message.chat.id, texts.language_is_set.format(language), reply_markup=keyboards.empty)


# add words

# TODO: not allow any special characters apart from "-"
# TODO: is there still timeout ?
@logged_execution
def handle_add_words(message, bot):
    language = db_model.get_current_language(pool, message.chat.id)
    if language is None:
        utils.handle_language_not_set(message, bot)
        return
    
    bot.set_state(message.from_user.id, states.AddWordsState.add_words, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["language"] = language
    
    bot.reply_to(message, texts.add_words_instruction_1)


@logged_execution
def process_adding_words(message, bot):
    words = list(filter(
        lambda x: len(x) > 0,
        [w.strip().lower() for w in message.text.split("\n")]
    ))
    if len(words) == 0:
        bot.reply_to(message, texts.add_words_none_added)
        bot.delete_state(message.from_user.id, message.chat.id)
        return
    
    bot.reply_to(message, texts.add_words_instruction_2.format(words))
    bot.send_message(
        message.chat.id,
        texts.add_words_translate.format(words[0]),
        reply_markup=keyboards.empty
    )
    
    bot.set_state(message.from_user.id, states.AddWordsState.translate, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["words"] = words
        data["translations"] = []


@logged_execution
def process_word_translation_stop(message, bot):
    bot.delete_state(message.from_user.id, message.chat.id)
    bot.send_message(message.chat.id, texts.add_words_cancelled, reply_markup=keyboards.empty)
        

@logged_execution
def process_word_translation(message, bot):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["translations"].append(json.dumps([m.strip().lower() for m in message.text.split("/")]))
        
        if len(data["translations"]) == len(data["words"]): # translation is over
            db_model.update_vocab(pool, message.chat.id, data["language"], data["words"], data["translations"])
            bot.send_message(
                message.chat.id, texts.add_words_finished.format(len(data["words"])),
                reply_markup=keyboards.empty
            )
            bot.delete_state(message.from_user.id, message.chat.id)
        else:
            bot.send_message(
                message.chat.id, data["words"][len(data["translations"])],
                reply_markup=keyboards.empty
            )


# show words

# TODO: delete all unnecessary messages
@logged_execution
def handle_show_words(message, bot):
    language = db_model.get_current_language(pool, message.chat.id)
    if language is None:
        utils.handle_language_not_set(message, bot)
        return

    vocab = db_model.get_full_vocab(pool, message.chat.id, language)
    if len(vocab) == 0:
        bot.send_message(message.chat.id, texts.no_words_yet, reply_markup=keyboards.empty)
        return
    
    bot.send_message(
        message.chat.id,
        texts.words_count.format(len(vocab), language),
        reply_markup=keyboards.empty
    )

    for entry in vocab:
        word = word_utils.Word(entry)
        entry["score"] = word.get_overall_score()
        entry["n_trains"] = word.get_total_trains()
    
    # TODO: make all keyboards one time
    markup = keyboards.get_reply_keyboard(options.show_words_sort_options, ["/exit"], row_width=3)
    bot.send_message(message.chat.id, texts.choose_sorting, reply_markup=markup)
    
    bot.set_state(message.from_user.id, states.ShowWordsState.choose_sort, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["vocabulary"] = vocab
        data["original_command"] = message.text

  
@logged_execution  
def process_choose_word_sort(message, bot):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        if message.text not in options.show_words_sort_options:
            bot.reply_to(message, texts.sorting_not_supported.format(data["original_command"]))
            bot.delete_state(message.from_user.id, message.chat.id)
            return
        
        words = data["vocabulary"]
    
    # TODO: get rid of string constants
    if message.text == "a-z":
        words = sorted(words, key=lambda w: w["word"])
    elif message.text == "z-a":
        words = sorted(words, key=lambda w: w["word"])[::-1]
    elif message.text == "n trains ⬇️":
        words = sorted(words, key=lambda w: w["n_trains"])[::-1]
    elif message.text == "n trains ⬆️":
        words = sorted(words, key=lambda w: w["n_trains"])
    elif message.text == "time added ⬇️":
        words = sorted(words, key=lambda w: w["added_timestamp"])[::-1]
    elif message.text == "time added ⬆️":
        words = sorted(words, key=lambda w: w["added_timestamp"])
    elif message.text == "score ⬇️":
        unknown_score = list(filter(lambda w: w["score"] is None, words))
        known_score = list(filter(lambda w: w["score"] is not None, words))
        words = sorted(known_score, key=lambda w: w["score"])[::-1]
        words.extend(unknown_score)
    elif message.text == "score ⬆️":
        unknown_score = list(filter(lambda w: w["score"] is None, words))
        known_score = list(filter(lambda w: w["score"] is not None, words))
        words = sorted(known_score, key=lambda w: w["score"])
        words.extend(unknown_score)
        
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["vocabulary"] = words
        data["batch_number"] = 0
    bot.set_state(message.from_user.id, states.ShowWordsState.show_words, message.chat.id)
    process_show_words_batch_next(message, bot)


@logged_execution  
def process_show_words_batch_unknown(message, bot):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        bot.send_message(
            message.chat.id,
            texts.unknown_command.format(data["original_command"]),
            reply_markup=keyboards.empty
        )
    bot.delete_state(message.from_user.id, message.chat.id)


@logged_execution  
def process_show_words_batch_next(message, bot):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        batch_number = data["batch_number"]
        words = data["vocabulary"]

    words_batch = words[
        batch_number * constants.SHOW_WORDS_BATCH_SIZE:
        (batch_number + 1) * constants.SHOW_WORDS_BATCH_SIZE
    ]
    words_formatted = [word_utils.format_word_for_listing(word) for word in words_batch]
    
    n_pages = len(words) // constants.SHOW_WORDS_BATCH_SIZE
    if len(words) % constants.SHOW_WORDS_BATCH_SIZE > 0:
        n_pages += 1
    
    if len(words_batch) < constants.SHOW_WORDS_BATCH_SIZE:
        # we've run out of words 
        markup = keyboards.empty
        bot.delete_state(message.from_user.id, message.chat.id)
    else:    
        markup = keyboards.get_reply_keyboard(["/exit", "/next"])
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data["batch_number"] += 1

    bot.send_message(
        message.chat.id,
        texts.word_formatted.format(batch_number + 1, n_pages, "\n".join(words_formatted)),
        reply_markup=markup, parse_mode="MarkdownV2"
    )


# show language info

@logged_execution
def handle_show_current_language(message, bot):
    current_language = db_model.get_current_language(pool, message.chat.id)
    if current_language is not None:
        bot.send_message(message.chat.id, texts.current_language.format(current_language))
    else:
        utils.handle_language_not_set(message, bot)


@logged_execution
def handle_show_languages(message, bot):
    languages = sorted(db_model.get_available_languages(pool, message.chat.id))
    current_language = db_model.get_current_language(pool, message.chat.id)
    
    if len(languages) == 0:
        bot.send_message(
            message.chat.id,
            texts.show_languages_none,
            reply_markup=keyboards.empty
        )
    else:
        languages = [
            options.show_languages_mark_current[l == current_language].format(l)
            for l in languages
        ]
        bot.send_message(
            message.chat.id,
            texts.available_languages.format(len(languages), "\n".join(languages)),
            reply_markup=keyboards.empty
        )


# delete language

@logged_execution
def handle_delete_language(message, bot):
    language = db_model.get_current_language(pool, message.chat.id)
    if language is None:
        utils.handle_language_not_set(message, bot)
        return
    
    markup = keyboards.get_reply_keyboard(options.delete_are_you_sure)
    bot.send_message(
        message.chat.id,
        texts.delete_language_warning.format(language),
        reply_markup=markup
    )
    bot.set_state(message.from_user.id, states.DeleteLanguageState.init, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["language"] = language


@logged_execution
def process_delete_language(message, bot):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        language = data["language"]

    if message.text not in options.delete_are_you_sure:
        bot.reply_to(message, texts.unknown_command_short)
        return
    
    bot.delete_state(message.from_user.id, message.chat.id)
    
    if options.delete_are_you_sure[message.text]:
        db_model.delete_language(pool, message.chat.id, language)
        bot.send_message(
            message.chat.id,
            texts.delete_language_final.format(language),
            reply_markup=keyboards.empty
        )
    else:
        bot.send_message(message.chat.id, texts.cancel_short, reply_markup=keyboards.empty)


# delete words

# TODO: delete words from groups too
@logged_execution
def handle_delete_words(message, bot):
    language = db_model.get_current_language(pool, message.chat.id)
    if language is None:
        utils.handle_language_not_set(message, bot)
        return

    bot.send_message(message.chat.id, texts.delete_words_start)
    bot.set_state(message.from_user.id, states.DeleteWordsState.init, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["language"] = language


@logged_execution
def process_deleting_words(message, bot):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        language = data["language"]
    bot.delete_state(message.from_user.id, message.chat.id)
    
    words = message.text.split("\n")
    existing_words = db_model.get_words_from_vocab(pool, message.chat.id, language, words)
    db_model.delete_words_from_vocab(pool, message.chat.id, language, words)
    
    bot.send_message(
        message.chat.id,
        texts.deleted_words_list.format(
            len(existing_words),
            "\n".join([entry["word"] for entry in existing_words]),
            "" if len(existing_words) == len(words) else texts.deleted_words_unknown
        )
    )


# create group

@logged_execution
def handle_create_group(message, bot):
    language = db_model.get_current_language(pool, message.chat.id)
    if language is None:
        utils.handle_language_not_set(message, bot)
        return

    bot.send_message(message.chat.id, texts.create_group_name)
    bot.set_state(message.from_user.id, states.CreateGroupState.init, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["language"] = language


@logged_execution
def process_group_creation(message, bot):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        language = data["language"]
    bot.delete_state(message.from_user.id, message.chat.id)

    # TODO: check latin letters and underscores
    # TODO: check name collisions with shared groups
    group_name = message.text.strip()
    if len(db_model.get_group_by_name(pool, message.chat.id, language, group_name)) > 0:
        bot.reply_to(message, texts.group_already_exists)
        return
    
    group_id = blake2b(digest_size=10)
    group_key = "{}-{}-{}".format(message.chat.id, language, group_name)
    group_id.update(group_key.encode())
    
    db_model.add_group(pool, message.chat.id, language=language,
                       group_name=group_name, group_id=group_id.hexdigest(), is_creator=True)
    bot.send_message(message.chat.id, texts.group_created)

# show groups

@logged_execution
def handle_show_groups(message, bot):
    utils.suggest_group_choises(message, bot, states.ShowGroupsState.init)


@logged_execution
def process_show_group_contents(message, bot):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        language = data["language"]
        group_names = data["group_names"]
    
    groups = db_model.get_group_by_name(pool, message.chat.id, language, message.text)
    markup = keyboards.get_reply_keyboard(group_names, ["/exit"], row_width=3)
    
    if len(groups) != 1:
        bot.reply_to(message, texts.no_such_group, reply_markup=markup)
        return
    
    group_id = groups[0]["group_id"].decode("utf-8")
    group_contents = sorted(db_model.get_group_contents(pool, group_id), key=lambda w: w["word"])
    
    for entry in group_contents:
        word = word_utils.Word(entry)
        entry["score"] = word.get_overall_score()
        entry["n_trains"] = word.get_total_trains()
    
    if len(group_contents) == 0:
        bot.reply_to(message, texts.show_group_empty, reply_markup=keyboards.empty)
        bot.delete_state(message.from_user.id, message.chat.id)
        return
    
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["batch_number"] = 0
        data["vocabulary"] = group_contents
        
    bot.set_state(message.from_user.id, states.ShowWordsState.show_words, message.chat.id)
    process_show_words_batch_next(message, bot)


# group add words
# TODO: delete all unnecessary messages
@logged_execution
def handle_group_add_words(message, bot):
    utils.suggest_group_choises(message, bot, states.AddGroupWordsState.choose_group)
    

@logged_execution
def process_save_group_edit(message, bot):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        language = data["language"]
        vocabulary = data["vocabulary"]
        masks = data["masks"]
        group_id = data["group_id"]
        group_name = data["group_name"]
        action = data["action"]
    
    bot.delete_state(message.from_user.id, message.chat.id)
    
    chosen_words = []
    for entity, mask in zip(vocabulary, masks):
        if action == "add" and mask == 1:
            chosen_words.append(entity["word"])
        if action == "delete" and mask == 0:
            chosen_words.append(entity["word"])
    n_edited_words = utils.save_words_edit_to_group(message.chat.id, language, group_id, chosen_words, action)
    
    bot.reply_to(
        message,
        texts.group_edit_finished.format(group_name, action, n_edited_words, "\n".join(sorted(list(chosen_words)))),
        reply_markup=keyboards.empty
    )


@logged_execution
def process_choose_words_batch_for_group_next(message, bot):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        batch_number = data["batch_number"]
        batch_size = data["batch_size"]
        vocabulary = data["vocabulary"]
    
    if batch_number * batch_size > len(vocabulary):
        # the words have ended
        bot.send_message(message.chat.id, texts.group_edit_no_more_words, reply_keyboard=keyboards.empty)
        process_save_group_edit(message, bot)
        return
    
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["batch_number"] += 1
        data["is_start"] = True
    process_choose_words_batch_for_group(message, bot)


@logged_execution
def process_choose_words_batch_for_group(message, bot):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        vocabulary = data["vocabulary"]
        masks = data["masks"]
        batch_number = data["batch_number"]
        is_start = data["is_start"]
        batch_size = data["batch_size"]

    n_batches = utils.get_number_of_batches(constants.GROUP_ADD_WORDS_BATCH_SIZE, len(vocabulary))

    batch = vocabulary[batch_number * batch_size:(batch_number + 1) * batch_size]
    batch_mask = masks[batch_number * batch_size:(batch_number + 1) * batch_size]
    
    additional_commands = ["/cancel", "/exit"]
    if batch_number + 1 < n_batches:
        additional_commands.append("/next")
    
    markup = keyboards.get_masked_choices(batch, batch_mask, additional_commands=additional_commands)
    
    if is_start:
        bot.send_message(
            message.chat.id,
            texts.group_add_choose.format(batch_number + 1, n_batches),
            reply_markup=markup
        )
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data["is_start"] = False
    elif word_utils.get_word_from_group_action(message.text) not in [entry["word"] for entry in batch]:
        logger.debug(f"word clicked: {word_utils.get_word_from_group_action(message.text)}")
        bot.send_message(message.chat.id, texts.group_edit_unknown_word, reply_markup=markup)
    else:
        current_word = word_utils.get_word_from_group_action(message.text)
        word_idx = word_utils.get_word_idx(batch, current_word)
        batch_mask[word_idx] = (batch_mask[word_idx] + 1) % 2
        
        markup = keyboards.get_masked_choices(batch, batch_mask, additional_commands=additional_commands)
        bot.send_message(message.chat.id, texts.group_add_confirm, reply_markup=markup)
        
        masks[batch_number * constants.GROUP_ADD_WORDS_BATCH_SIZE + word_idx] = batch_mask[word_idx]
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data["masks"] = masks


def process_choose_sorting_to_add_words(message, bot):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        vocabulary = data["vocabulary"]
    
    if message.text not in options.group_add_words_sort_options:
        markup = keyboards.get_reply_keyboard(options.group_add_words_sort_options, ["/exit"])
        bot.reply_to(
            message,
            texts.sorting_not_supported,
            reply_markup=markup
        )
        return
    
    if message.text == "a-z":
        vocabulary = sorted(vocabulary, key=lambda x: x["translation"])
    elif message.text == "time added ⬇️":
        vocabulary = sorted(vocabulary, key=lambda x: x["added_timestamp"])[::-1]

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["vocabulary"] = vocabulary
    bot.set_state(message.from_user.id, states.AddGroupWordsState.choose_words, message.chat.id)
    process_choose_words_batch_for_group(message, bot)


@logged_execution
def handle_choose_group_to_add_words(message, bot):
    # TODO: exception cannot access local variable 'language' where it is not associated with a value
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        language = data["language"]
        group_names = data["group_names"]
    
    groups = db_model.get_group_by_name(pool, message.chat.id, language, message.text)
    markup = keyboards.get_reply_keyboard(group_names, ["/exit"], row_width=3)
    
    if len(groups) != 1:
        bot.reply_to(message, texts.no_such_group, reply_markup=markup)
        return

    if not groups[0]["is_creator"]:
        bot.delete_state(message.from_user.id, message.chat.id)
        bot.reply_to(message, texts.group_not_a_creator, reply_markup=keyboards.empty)
        return
    
    group_id = groups[0]["group_id"].decode("utf-8")
    vocabulary = db_model.get_full_vocab(pool, message.chat.id, language)
    words_in_group = set([entry["word"] for entry in db_model.get_group_contents(pool, group_id)])
    
    words_to_add = []
    for entry in vocabulary:
        if entry["word"] in words_in_group:
            continue
        words_to_add.append(entry)

    if len(words_to_add) == 0:
        bot.delete_state(message.from_user.id, message.chat.id)
        bot.reply_to(message, texts.group_edit_full)
        return

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["vocabulary"] = words_to_add
        data["masks"] = [0] * len(words_to_add)
        data["batch_number"] = 0
        data["is_start"] = True
        data["batch_size"] = constants.GROUP_ADD_WORDS_BATCH_SIZE
        data["group_id"] = group_id
        data["group_name"] = message.text
        data["action"] = "add"

    bot.set_state(message.from_user.id, states.AddGroupWordsState.choose_sorting, message.chat.id)
    bot.send_message(
        message.chat.id,
        texts.choose_sorting,
        reply_markup=keyboards.get_reply_keyboard(options.group_add_words_sort_options, ["/exit"])
    )
