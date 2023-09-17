from hashlib import blake2b
import json

import database.model as db_model
from logs import logger, logged_execution
from user_interaction import config, options, texts
import word as word_utils

from bot import constants, keyboards, states, utils


# common
@logged_execution
def process_exit(message, bot, pool):
    exit_message = bot.send_message(message.chat.id, texts.exited, reply_markup=keyboards.empty)
    
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        if "init_message" in data:
            utils.clear_history(bot, message.chat.id, data["init_message"], exit_message.id)
            
    bot.delete_state(message.from_user.id, message.chat.id)


@logged_execution
def process_cancel(message, bot, pool):
    cancel_message = bot.send_message(message.chat.id, texts.cancel_short, reply_markup=keyboards.empty)
    
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        if "init_message" in data:
            utils.clear_history(bot, message.chat.id, data["init_message"], cancel_message.id)
            
    bot.delete_state(message.from_user.id, message.chat.id)


# TODO: add user to db after hitting /help or /start
@logged_execution
def handle_help(message, bot, pool):
    bot.send_message(message.chat.id, texts.help_message, reply_markup=keyboards.empty)


@logged_execution
def handle_forget_me(message, bot, pool):
    markup = keyboards.get_reply_keyboard(options.delete_are_you_sure)
    bot.set_state(message.from_user.id, states.ForgetMeState.init, message.chat.id)
    bot.send_message(message.chat.id, texts.forget_me_warning, reply_markup=markup)


# forget me
@logged_execution
def process_forget_me(message, bot, pool):
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
def handle_unknown(message, bot, pool):
    # bot.reply_to(message, texts.unknown_message)
    logger.warning(f"Unknown message! chat_id: {message.chat.id}, message: {message.text}")


# set language

# TODO: check language name (same as group name)
@logged_execution
def handle_set_language(message, bot, pool):
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


@logged_execution
def process_setting_language(message, bot, pool):
    language = message.text.lower().strip()
    user_info = db_model.get_user_info(pool, message.chat.id)
    
    if len(user_info) == 0: # new user!
        bot.send_message(message.chat.id, texts.welcome, reply_markup=keyboards.empty)
        db_model.create_user(pool, message.chat.id)
    
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        if language not in db_model.get_available_languages(pool, message.chat.id):
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
def handle_add_words(message, bot, pool):
    language = db_model.get_current_language(pool, message.chat.id)
    if language is None:
        utils.handle_language_not_set(message, bot)
        return
    
    bot.set_state(message.from_user.id, states.AddWordsState.add_words, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["language"] = language
    
    bot.reply_to(message, texts.add_words_instruction_1)


@logged_execution
def process_adding_words(message, bot, pool):
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
def process_word_translation_stop(message, bot, pool):
    bot.delete_state(message.from_user.id, message.chat.id)
    bot.send_message(message.chat.id, texts.add_words_cancelled, reply_markup=keyboards.empty)
        

@logged_execution
def process_word_translation(message, bot, pool):
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
def handle_show_words(message, bot, pool):
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
def process_choose_word_sort(message, bot, pool):
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
    process_show_words_batch_next(message, bot, pool)


@logged_execution  
def process_show_words_batch_unknown(message, bot, pool):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        bot.send_message(
            message.chat.id,
            texts.unknown_command.format(data["original_command"]),
            reply_markup=keyboards.empty
        )
    bot.delete_state(message.from_user.id, message.chat.id)


@logged_execution  
def process_show_words_batch_next(message, bot, pool):
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
def handle_show_current_language(message, bot, pool):
    current_language = db_model.get_current_language(pool, message.chat.id)
    if current_language is not None:
        bot.send_message(message.chat.id, texts.current_language.format(current_language))
    else:
        utils.handle_language_not_set(message, bot)


@logged_execution
def handle_show_languages(message, bot, pool):
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
def handle_delete_language(message, bot, pool):
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
def process_delete_language(message, bot, pool):
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
def handle_delete_words(message, bot, pool):
    language = db_model.get_current_language(pool, message.chat.id)
    if language is None:
        utils.handle_language_not_set(message, bot)
        return

    bot.send_message(message.chat.id, texts.delete_words_start)
    bot.set_state(message.from_user.id, states.DeleteWordsState.init, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["language"] = language


@logged_execution
def process_deleting_words(message, bot, pool):
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
def handle_create_group(message, bot, pool):
    language = db_model.get_current_language(pool, message.chat.id)
    if language is None:
        utils.handle_language_not_set(message, bot)
        return

    bot.send_message(message.chat.id, texts.create_group_name)
    bot.set_state(message.from_user.id, states.CreateGroupState.init, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["language"] = language


@logged_execution
def process_group_creation(message, bot, pool):
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
def handle_show_groups(message, bot, pool):
    utils.suggest_group_choices(message, bot, pool, states.ShowGroupsState.init)


@logged_execution
def process_show_group_contents(message, bot, pool):
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
    process_show_words_batch_next(message, bot, pool)


# group add words
# TODO: delete all unnecessary messages
@logged_execution
def handle_group_add_words(message, bot, pool):
    utils.suggest_group_choices(message, bot, pool, states.AddGroupWordsState.choose_group)


@logged_execution
def handle_choose_group_to_add_words(message, bot, pool):
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


@logged_execution
def process_choose_sorting_to_add_words(message, bot, pool):
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
    process_choose_words_batch_for_group(message, bot, pool)
    

@logged_execution
def process_save_group_edit(message, bot, pool):
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
    n_edited_words = utils.save_words_edit_to_group(pool, message.chat.id, language, group_id, chosen_words, action)
    logger.debug(f"n_edited_words: {n_edited_words}")
    
    bot.reply_to(
        message,
        texts.group_edit_finished.format(group_name, action, n_edited_words, "\n".join(sorted(list(chosen_words)))),
        reply_markup=keyboards.empty
    )


@logged_execution
def process_choose_words_batch_for_group_next(message, bot, pool):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        batch_number = data["batch_number"]
        batch_size = data["batch_size"]
        vocabulary = data["vocabulary"]
    
    if batch_number * batch_size > len(vocabulary):
        # the words have ended
        bot.send_message(message.chat.id, texts.group_edit_no_more_words, reply_keyboard=keyboards.empty)
        process_save_group_edit(message, bot, pool)
        return
    
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["batch_number"] += 1
        data["is_start"] = True
    process_choose_words_batch_for_group(message, bot, pool)


@logged_execution
def process_choose_words_batch_for_group(message, bot, pool):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        vocabulary = data["vocabulary"]
        masks = data["masks"]
        batch_number = data["batch_number"]
        is_start = data["is_start"]
        batch_size = data["batch_size"]
        action = data["action"]
        group_name = data["group_name"]

    n_batches = utils.get_number_of_batches(constants.GROUP_ADD_WORDS_BATCH_SIZE, len(vocabulary))

    batch = vocabulary[batch_number * batch_size:(batch_number + 1) * batch_size]
    batch_mask = masks[batch_number * batch_size:(batch_number + 1) * batch_size]
    
    additional_commands = ["/cancel", "/exit"]
    logger.debug(f"batch_number: {batch_number}, n_batches: {n_batches}")
    if batch_number + 1 < n_batches:
        additional_commands.append("/next")
    
    markup = keyboards.get_masked_choices(batch, batch_mask, additional_commands=additional_commands)
    
    if is_start:
        bot.send_message(
            message.chat.id,
            texts.group_edit_choose.format(action, group_name, batch_number + 1, n_batches),
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
        bot.send_message(message.chat.id, texts.group_edit_confirm, reply_markup=markup)
        
        masks[batch_number * constants.GROUP_ADD_WORDS_BATCH_SIZE + word_idx] = batch_mask[word_idx]
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data["masks"] = masks


# group delete words
@logged_execution
def handle_group_delete_words(message, bot, pool):
    utils.suggest_group_choices(message, bot, pool, states.DeleteGroupWordsState.choose_group)


@logged_execution
def handle_choose_group_to_delete_words(message, bot, pool):
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
    words_in_group = db_model.get_group_contents(pool, group_id)
    
    if len(words_in_group) == 0:
        bot.delete_state(message.from_user.id, message.chat.id)
        bot.reply_to(message, texts.group_edit_empty)
        return

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["vocabulary"] = words_in_group
        data["masks"] = [1] * len(words_in_group)
        data["batch_number"] = 0
        data["is_start"] = True
        data["batch_size"] = constants.GROUP_ADD_WORDS_BATCH_SIZE
        data["group_id"] = group_id
        data["group_name"] = message.text
        data["action"] = "delete"

    bot.set_state(message.from_user.id, states.DeleteGroupWordsState.choose_sorting, message.chat.id)
    bot.send_message(
        message.chat.id,
        texts.choose_sorting,
        reply_markup=keyboards.get_reply_keyboard(options.group_add_words_sort_options, ["/exit"])
    )


# TODO: merge with process_choose_sorting_to_add_words, only state is different
@logged_execution
def process_choose_sorting_to_delete_words(message, bot, pool):
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
    bot.set_state(message.from_user.id, states.DeleteGroupWordsState.choose_words, message.chat.id)
    process_choose_words_batch_for_group(message, bot, pool)


# delete group

@logged_execution
def handle_delete_group(message, bot, pool):
    utils.suggest_group_choices(message, bot, pool, states.DeleteGroupState.select_group)


@logged_execution
def process_group_deletion_check_sure(message, bot, pool):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        language = data["language"]
    
    groups = db_model.get_group_by_name(pool, message.chat.id, language, message.text)
    
    if len(groups) == 0:
        bot.reply_to(message, texts.no_such_group)
        utils.suggest_group_choices(message, bot, pool, states.DeleteGroupState.select_group)
        return

    group_id = groups[0]["group_id"].decode("utf-8")
    group_name = groups[0]["group_name"].decode("utf-8")
    is_creator = groups[0]["is_creator"]
    
    if not groups[0]["is_creator"]:
        bot.delete_state(message.from_user.id, message.chat.id)
        bot.reply_to(message, texts.group_not_a_creator, reply_markup=keyboards.empty)
        return
    
    bot.set_state(message.from_user.id, states.DeleteGroupState.are_you_sure, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["group_name"] = group_name
        data["group_id"] = group_id
        data["is_creator"] = is_creator
    
    markup = keyboards.get_reply_keyboard(options.delete_are_you_sure)
    bot.send_message(
        message.chat.id,
        texts.delete_group_warning.format(group_name, language),
        reply_markup=markup
    )


@logged_execution
def process_group_deletion(message, bot, pool):
    # TODO: when sharing think of local / global deletions (use is_creator)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        group_name = data["group_name"]
        group_id = data["group_id"]
        # is_creator = data["is_creator"]
    
    if message.text not in options.delete_are_you_sure:
        markup = keyboards.get_reply_keyboard(options.delete_are_you_sure)
        bot.reply_to(message, texts.unknown_command_short, reply_markup=markup)
        return
    
    bot.delete_state(message.from_user.id, message.chat.id)
    
    if not options.delete_are_you_sure[message.text]:
        bot.send_message(
            message.chat.id, texts.delete_group_cancel,
            reply_markup=keyboards.empty
        )
        return
    
    db_model.delete_group(pool, group_id)
    bot.delete_state(message.from_user.id, message.chat.id)
    bot.send_message(message.chat.id, texts.delete_group_success.format(group_name))


# TRAIN

@logged_execution
def handle_train(message, bot, pool):
    language = db_model.get_current_language(pool, message.chat.id)
    if language is None:
        utils.handle_language_not_set(message, bot)
        return

    markup = keyboards.get_reply_keyboard(options.train_strategy_options, ["/cancel"])
    reply_message = bot.send_message(
        message.chat.id,
        texts.training_init,
        reply_markup=markup
    )
    
    bot.set_state(message.from_user.id, states.TrainState.choose_strategy, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["language"] = language
        data["init_message"] = reply_message.id


@logged_execution
def init_direction_choice(message, bot, pool):
    markup = keyboards.get_reply_keyboard(options.train_direction_options, ["/cancel"])
    bot.send_message(
        message.chat.id,
        texts.training_direction,
        reply_markup=markup
    )
    bot.set_state(message.from_user.id, states.TrainState.choose_direction, message.chat.id)
    

@logged_execution
def process_choose_strategy(message, bot, pool):
    if message.text not in options.train_strategy_options:
        markup = keyboards.get_reply_keyboard(options.train_strategy_options, ["/cancel"])
        bot.reply_to(message, texts.training_strategy_unknown, reply_markup=markup)
        return
    
    if message.text == "group":
        utils.suggest_group_choices(message, bot, pool, states.TrainState.choose_group)
    else:
        # bot.set_state(message.from_user.id, states.TrainState.choose_direction, message.chat.id)
        init_direction_choice(message, bot, pool)

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["strategy"] = message.text


@logged_execution
def process_choose_group_for_training(message, bot, pool):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        language = data["language"]
    
    groups = db_model.get_group_by_name(
        pool, message.chat.id, language, message.text
    )
    
    if len(groups) == 0:
        bot.reply_to(message, texts.no_such_group.format("/train"), reply_markup=keyboards.empty)
        utils.suggest_group_choices(message, bot, pool, states.TrainState.choose_group)
        return

    group_id = groups[0]["group_id"].decode("utf-8")
    group_name = message.text
    init_direction_choice(message, bot, pool)
    
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["group_id"] = group_id
        data["group_name"] = group_name


@logged_execution
def process_choose_direction(message, bot, pool):
    if message.text not in options.train_direction_options.keys():
        markup = keyboards.get_reply_keyboard(options.train_direction_options, ["/cancel"])
        bot.reply_to(message, texts.training_direction_unknown, reply_markup=markup)
        return
    
    bot.set_state(message.from_user.id, states.TrainState.choose_duration, message.chat.id)
    markup = keyboards.get_reply_keyboard(options.train_duration_options, ["/cancel"])
    bot.send_message(
        message.chat.id,
        texts.training_duration,
        reply_markup=markup
    )
    
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["direction"] = options.train_direction_options[message.text]


@logged_execution
def process_choose_duration(message, bot, pool):
    if not message.text.isdigit() and message.text not in options.train_duration_options:
        markup = keyboards.get_reply_keyboard(options.train_duration_options, ["/cancel"])
        bot.reply_to(message, texts.training_duration_unknown, reply_markup=markup)
        return
    
    bot.set_state(message.from_user.id, states.TrainState.choose_hints, message.chat.id)
    markup = keyboards.get_reply_keyboard(options.train_hints_options, ["/cancel"])
    bot.send_message(
        message.chat.id,
        texts.training_hints,
        reply_markup=markup
    )

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["duration"] = int(message.text) if message.text.isdigit() else config.TRAIN_MAX_N_WORDS


@logged_execution
def process_choose_hints(message, bot, pool):
    if message.text not in options.train_hints_options:
        markup = keyboards.get_reply_keyboard(options.train_hints_options, ["/cancel"])
        bot.reply_to(message, texts.training_hints_unknown, reply_markup=markup)
        return
    
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["hints"] = message.text
        data["session_id"] = db_model.get_current_time()
        
        language = data["language"]
        strategy = data["strategy"]
        direction = data["direction"]
        duration = data["duration"]
        hints = data["hints"]
        session_id = data["session_id"]
        group_id = data.get("group_id")
        group_name = data.get("group_name")
        init_message = data["init_message"]
    
    db_model.init_training_session(
        pool, message.chat.id,
        session_id, strategy, language, direction, duration, hints
    )
    if strategy != "group":
        db_model.create_training_session(pool, message.chat.id, session_id, strategy, language, direction, duration)
    else:
        db_model.create_group_training_session(pool, message.chat.id, session_id, strategy, language, direction, duration, group_id)
    
    words = db_model.get_training_words(pool, message.chat.id, session_id)
    
    if len(words) == 0:
        bot.delete_state(message.from_user.id, message.chat.id)
        bot.send_message(
            message.chat.id,
            texts.training_no_words_found,
            reply_markup=keyboards.empty
        )
        return
    
    train_message = bot.send_message(
        message.chat.id,
        texts.training_start.format(
            strategy, len(words),
            direction, hints,
            texts.training_start_group.format(group_name) if strategy == "group" else ""
        ),
        reply_markup=keyboards.empty
    )
    if len(words) < duration and duration != config.TRAIN_MAX_N_WORDS:
        bot.send_message(
            message.chat.id,
            texts.training_fewer_words,
            reply_markup=keyboards.empty
        )
    
    utils.clear_history(bot, message.chat.id, init_message, train_message.id)

    bot.set_state(message.from_user.id, states.TrainState.train, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["words"] = words
        data["step"] = 0
        data["scores"] = []
    
    handle_train_step(message, bot, pool)


@logged_execution
def handle_train_step_stop(message, bot, pool):
    bot.send_message(
        message.chat.id,
        texts.training_stopped,
        reply_markup=keyboards.empty
    )
    bot.delete_state(message.from_user.id, message.chat.id)


@logged_execution
def handle_train_step(message, bot, pool):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        step = data["step"]
        words = data["words"]
        scores = data["scores"]
        hints = data["hints"]
        direction = data["direction"]
        session_id = data["session_id"]
        language = data["language"]
    
    logger.debug(f"step: {step}, words: {words}, scores: {scores}, hints: {hints}, direction: {direction}")
    
    if step != 0: # not a first iteration
        word = words[step - 1]
        is_correct = word_utils.compare_user_input_with_db(
            message.text,
            word,
            hints,
            direction
        )
        scores.append(int(is_correct))
        if is_correct:
            bot.send_message(
                message.chat.id,
                texts.train_correct_answer,
                reply_markup=keyboards.empty
            )
        else:
            bot.send_message(
                message.chat.id,
                texts.train_wrong_answer.format(
                    word_utils.get_translation(word, direction)
                ),
                reply_markup=keyboards.empty
            )

    if step == len(words): # training complete
        # TODO: different messages for different results
        if hints == "no hints":
            db_model.set_training_scores(
                pool, message.chat.id, session_id,
                list(range(1, len(words) + 1)), scores
            )
            db_model.update_final_scores(pool, message.chat.id, session_id, language, direction)
        else:
            bot.send_message(
                message.chat.id, texts.training_no_scores
            )
        bot.send_message(
            message.chat.id,
            texts.training_results.format(sum(scores), len(words)),
            reply_markup=keyboards.empty
        )
        bot.delete_state(message.from_user.id, message.chat.id)
        return
    
    next_word = words[step]
    hint_words = word_utils.sample_hints(next_word, words, 3)
    bot.send_message(
        message.chat.id,
        word_utils.format_train_message(
            word_utils.get_word(next_word, direction),
            word_utils.get_translation(next_word, direction),
            hints
        ),
        reply_markup=keyboards.format_train_buttons(
            word_utils.get_translation(next_word, direction),
            [word_utils.get_translation(hint, direction) for hint in hint_words],
            hints
        ),
        parse_mode="MarkdownV2"
    )
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["step"] += 1
        data["scores"] = scores
