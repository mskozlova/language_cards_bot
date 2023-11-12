import datetime
import json

import database.queries as queries
from database.utils import execute_select_query, execute_update_query

WORDS_UPDATE_BUCKET_SIZE = 20
GROUPS_UPDATE_BUCKET_SIZE = 20


def get_current_time():
    return int(datetime.datetime.timestamp(datetime.datetime.now()))


def get_state(pool, chat_id):
    results = execute_select_query(pool, queries.get_user_state, chat_id=chat_id)
    if len(results) == 0:
        return None
    if results[0]["state"] is None:
        return None
    return json.loads(results[0]["state"])


def set_state(pool, chat_id, state):
    execute_update_query(
        pool, queries.set_user_state, chat_id=chat_id, state=json.dumps(state)
    )


def clear_state(pool, chat_id):
    execute_update_query(pool, queries.set_user_state, chat_id=chat_id, state=None)


def create_user(pool, chat_id):
    execute_update_query(pool, queries.create_user, chat_id=chat_id)


def get_user_info(pool, chat_id):
    return execute_select_query(pool, queries.get_user_info, chat_id=chat_id)


def update_vocab(pool, chat_id, language, words, translations):
    assert len(words) == len(
        translations
    ), "words and translations should have the same length. len(words) = {}, len(translations) = {}".format(
        len(words), len(translations)
    )
    added_timestamp = get_current_time()

    for i in range(0, len(words), WORDS_UPDATE_BUCKET_SIZE):
        execute_update_query(
            pool,
            queries.bulk_update_words,
            chat_id=chat_id,
            language=language.encode(),
            words=words[i : i + WORDS_UPDATE_BUCKET_SIZE],
            translations=translations[i : i + WORDS_UPDATE_BUCKET_SIZE],
            added_timestamp=added_timestamp,
        )


def delete_user(pool, chat_id):
    execute_update_query(pool, queries.delete_user, chat_id=chat_id)


def delete_language(pool, chat_id, language):
    execute_update_query(
        pool, queries.delete_language, chat_id=chat_id, language=language.encode()
    )


def get_user_vocabs(pool, chat_id):
    return execute_select_query(pool, queries.get_user_vocabs, chat_id=chat_id)


def get_full_vocab(pool, chat_id, language):
    return execute_select_query(
        pool, queries.get_full_vocab, chat_id=chat_id, language=language.encode()
    )


def get_words_from_vocab(pool, chat_id, language, words):
    return execute_select_query(
        pool,
        queries.get_words_from_vocab,
        chat_id=chat_id,
        language=language.encode(),
        words=words,
    )


def delete_words_from_vocab(pool, chat_id, language, words):
    execute_update_query(
        pool,
        queries.delete_words_from_vocab,
        chat_id=chat_id,
        language=language.encode(),
        words=words,
    )


def update_current_lang(pool, chat_id, language):
    execute_update_query(
        pool, queries.update_current_lang, chat_id=chat_id, language=language.encode()
    )


def get_available_languages(pool, chat_id):
    result = execute_select_query(
        pool, queries.get_available_languages, chat_id=chat_id
    )
    return [row["language"].decode() for row in result]


def user_add_language(pool, chat_id, language):
    execute_update_query(
        pool, queries.user_add_language, chat_id=chat_id, language=language.encode()
    )


def get_current_language(pool, chat_id):
    result = execute_select_query(pool, queries.get_current_language, chat_id=chat_id)
    if len(result) != 1:
        return None

    if result[0]["current_lang"] is None:
        return None

    return result[0]["current_lang"].decode()


def init_training_session(
    pool, chat_id, session_id, strategy, language, direction, duration, hints
):
    execute_update_query(
        pool,
        queries.init_training_session,
        chat_id=chat_id,
        session_id=session_id,
        strategy=strategy.encode(),
        language=language.encode(),
        direction=direction.encode(),
        duration=duration,
        hints=hints.encode(),
    )


def get_session_info(pool, chat_id, session_id):
    return execute_select_query(
        pool, queries.get_session_info, chat_id=chat_id, session_id=session_id
    )


def create_training_session(
    pool, chat_id, session_id, strategy, language, direction, duration
):
    execute_update_query(
        pool,
        queries.create_training_session,
        chat_id=chat_id,
        session_id=session_id,
        strategy=strategy.encode(),
        language=language.encode(),
        direction=direction.encode(),
        duration=duration,
    )


def create_group_training_session(
    pool, chat_id, session_id, strategy, language, direction, duration, group_id
):
    execute_update_query(
        pool,
        queries.create_group_training_session,
        chat_id=chat_id,
        session_id=session_id,
        strategy=strategy.encode(),
        language=language.encode(),
        direction=direction.encode(),
        duration=duration,
        group_id=group_id.encode(),
    )


def get_training_words(pool, chat_id, session_id):
    return execute_select_query(
        pool, queries.get_training_words, chat_id=chat_id, session_id=session_id
    )


def set_training_scores(pool, chat_id, session_id, word_idxs, scores):
    execute_update_query(
        pool,
        queries.set_training_scores,
        chat_id=chat_id,
        session_id=session_id,
        word_idxs=word_idxs,
        scores=scores,
    )


def update_final_scores(pool, chat_id, session_id, language, direction):
    execute_update_query(
        pool,
        queries.update_final_scores,
        chat_id=chat_id,
        session_id=session_id,
        language=language.encode(),
        direction=direction.encode(),
    )


def get_group_by_name(pool, chat_id, language, group_name):
    return execute_select_query(
        pool,
        queries.get_group_by_name,
        chat_id=chat_id,
        language=language.encode(),
        group_name=group_name.encode(),
    )


def add_group(pool, chat_id, language, group_name, group_id, is_creator):
    execute_update_query(
        pool,
        queries.add_group,
        chat_id=chat_id,
        language=language.encode(),
        group_name=group_name.encode(),
        group_id=group_id.encode(),
        is_creator=is_creator,
    )


def delete_group(pool, group_id):
    execute_update_query(pool, queries.delete_group, group_id=group_id.encode())


def get_all_groups(pool, chat_id, language):
    return execute_select_query(
        pool, queries.get_all_groups, chat_id=chat_id, language=language.encode()
    )


def get_group_contents(pool, group_id):
    return execute_select_query(
        pool, queries.get_group_contents, group_id=group_id.encode()
    )


def add_words_to_group(pool, chat_id, language, group_id, words):
    words_list = list(words)
    for i in range(0, len(words_list), GROUPS_UPDATE_BUCKET_SIZE):
        execute_update_query(
            pool,
            queries.bulk_update_group,
            chat_id=chat_id,
            language=language.encode(),
            group_id=group_id.encode(),
            words=words_list[i : i + GROUPS_UPDATE_BUCKET_SIZE],
        )


def delete_words_from_group(pool, chat_id, language, group_id, words):
    words_list = list(words)
    for i in range(0, len(words_list), GROUPS_UPDATE_BUCKET_SIZE):
        execute_update_query(
            pool,
            queries.bulk_update_group_delete,
            chat_id=chat_id,
            language=language.encode(),
            group_id=group_id.encode(),
            words=words_list[i : i + GROUPS_UPDATE_BUCKET_SIZE],
        )


def log_command(pool, chat_id, command):
    timestamp = get_current_time()
    execute_update_query(
        pool,
        queries.log_command,
        chat_id=chat_id,
        timestamp=timestamp,
        command=command,
    )


def truncate_tables(pool):
    for query in queries.truncate_tables_queries:
        execute_update_query(pool, query)
