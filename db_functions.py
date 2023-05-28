import datetime
import json

import ydb


USERS_TABLE_PATH = "users"
VOCABS_TABLE_PATH = "vocabularies"
GROUPS_TABLE_PATH = "groups"
GROUPS_CONTENTS_TABLE_PATH = "group_contents"
TRAINING_SESSIONS_TABLE_PATH = "training_sessions"
TRAINING_SESSIONS_INFO_TABLE_PATH = "training_session_info"
WORDS_UPDATE_BUCKET_SIZE = 20
GROUPS_UPDATE_BUCKET_SIZE = 20

VOCABS_UPDATE_VALUES = "(CAST({} AS Uint64), '{}', CAST('{}' AS Utf8), " \
                       "{}, {}, CAST({} AS Uint64), CAST({} AS Uint64), " \
                       "CAST('{}' AS Utf8), CAST({} AS Uint64))"
GROUP_UPDATE_VALUES = "(CAST({} AS Uint64), '{}', '{}', CAST('{}' AS Utf8))"


def get_nullable_str(value):
    if value is None:
        return "NULL"
    return "'{}'".format(value)


def get_nullable_float(value):
    if value is None:
        return "NULL"
    return float(value)


def get_new_session_id():
    return int(datetime.datetime.timestamp(datetime.datetime.now()))


# TODO: use prepared statement
# def update_user(pool, user):
#     def callee(session):
#         session.transaction().execute(
#             """
#             UPSERT INTO `{}` (chat_id, current_lang, languages) VALUES
#                 ({}, '{}', '{}');
#             """.format(
#                 USERS_TABLE_PATH, user.chat_id, user.current_lang,
#                 json.dumps(list(user.vocabs.keys()), ensure_ascii=False)
#             ),
#             commit_tx=True,
#         )

#     return pool.retry_operation_sync(callee)


def get_user_info(pool, chat_id):
    def callee(session):
        result_sets = session.transaction(ydb.SerializableReadWrite()).execute(
            """
            SELECT * FROM `{}`
            WHERE chat_id == {}
            """.format(
                USERS_TABLE_PATH, chat_id
            ),
            commit_tx=True,
        )
        return result_sets[0].rows

    return pool.retry_operation_sync(callee)


def bulk_update_words(pool, values):
    def callee(session):
        session.transaction().execute(
            """
            UPSERT INTO `{}` (chat_id, language, word, last_train_from, last_train_to, 
                score_from, score_to, translation, added_timestamp) VALUES
                {};
            """.format(
                VOCABS_TABLE_PATH, values
            ),
            commit_tx=True,
        )

    return pool.retry_operation_sync(callee)


def prepare_vocabs_data(chat_id, language, words):
    data_list = []
    for word, translation in words:
        data_list.append((
            VOCABS_UPDATE_VALUES.format(
                chat_id, language, word,
                "NULL", "NULL",
                "NULL", "NULL",
                translation,
                int(datetime.datetime.timestamp(datetime.datetime.now()))
            )
        ))
    return data_list


def update_vocab(pool, chat_id, language, words):
    data = prepare_vocabs_data(chat_id, language, words)
    for i in range(0, len(data), WORDS_UPDATE_BUCKET_SIZE):
        bulk_update_words(pool, ",\n".join(data[i:i+WORDS_UPDATE_BUCKET_SIZE]))


def delete_user(pool, chat_id):
    def callee(session):
        session.transaction().execute(
            """
            DELETE FROM `{}`
            WHERE chat_id == {};
            
            DELETE FROM `{}`
            WHERE chat_id == {};
            """.format(
                USERS_TABLE_PATH, chat_id,
                VOCABS_TABLE_PATH, chat_id
            ),
            commit_tx=True,
        )

    return pool.retry_operation_sync(callee)


def get_user_vocabs(pool, chat_id):
    def callee(session):
        result_sets = session.transaction(ydb.SerializableReadWrite()).execute(
            """
            SELECT * FROM `{}`
            WHERE chat_id == {}
            """.format(
                VOCABS_TABLE_PATH, chat_id
            ),
            commit_tx=True,
        )
        return result_sets[0].rows

    return pool.retry_operation_sync(callee)


def get_full_vocab(pool, chat_id, language):
    def callee(session):
        result_sets = session.transaction(ydb.SerializableReadWrite()).execute(
            """
            SELECT
                word,
                score_from,
                score_to,
                n_trains_from,
                n_trains_to,
                translation,
                added_timestamp,
            FROM `{}`
            WHERE
                chat_id == {}
                AND language == '{}'
            """.format(
                VOCABS_TABLE_PATH, chat_id, language
            ),
            commit_tx=True,
        )
        return result_sets[0].rows

    return pool.retry_operation_sync(callee)


def delete_language_from_vocab(pool, user):
    def callee(session):
        session.transaction().execute(
            """
            DELETE FROM `{}`
            WHERE chat_id == {} AND language == '{}'
            """.format(
                VOCABS_TABLE_PATH, user.chat_id, user.current_lang
            ),
            commit_tx=True,
        )

    return pool.retry_operation_sync(callee)


def get_words_from_vocab(pool, chat_id, language, words):
    def callee(session):
        result_sets = session.transaction().execute(
            """    
            SELECT word FROM `{}`
            WHERE
                chat_id == {}
                AND language == '{}'
                AND word IN ({})
            """.format(
                VOCABS_TABLE_PATH, chat_id, language,
                ",".join("'{}'".format(word) for word in words)
            ),
            commit_tx=True,
        )
        return result_sets[0].rows

    return pool.retry_operation_sync(callee)


def delete_words_from_vocab(pool, chat_id, language, words):
    # TODO: delete from training sessions
    def callee(session):
        session.transaction().execute(
            """    
            DELETE FROM `{}`
            WHERE
                chat_id == {}
                AND language == '{}'
                AND word IN ({})
            """.format(
                VOCABS_TABLE_PATH, chat_id, language,
                ",".join("'{}'".format(word) for word in words)
            ),
            commit_tx=True,
        )

    return pool.retry_operation_sync(callee)


def update_current_lang(pool, chat_id, language):
    def callee(session):
        session.transaction().execute(
            """
            UPDATE `{}`
            SET current_lang = '{}'
            WHERE chat_id == {};
            """.format(
                USERS_TABLE_PATH, language, chat_id
            ),
            commit_tx=True,
        )

    return pool.retry_operation_sync(callee)


def get_available_languages(pool, chat_id):
    def callee(session):
        result_sets = session.transaction().execute(
            """
            SELECT DISTINCT language
            FROM `{}`
            WHERE chat_id == {}
            """.format(
                VOCABS_TABLE_PATH, chat_id
            ),
            commit_tx=True,
        )
        return [row["language"].decode("utf-8") for row in result_sets[0].rows]

    return pool.retry_operation_sync(callee)


def get_current_language(pool, chat_id):
    def callee(session):
        result_sets = session.transaction().execute(
            """
            SELECT current_lang
            FROM `{}`
            WHERE chat_id == {}
            """.format(
                USERS_TABLE_PATH, chat_id
            ),
            commit_tx=True,
        )
        raw_result = result_sets[0].rows
        return raw_result[0]["current_lang"] if len(raw_result) == 1 else None

    return pool.retry_operation_sync(callee)


def init_training_session(pool, chat_id, session_info):
    def callee(session):
        session.transaction().execute(
            """
            $chat_id = {};
            $session_id = {};
            $strategy = "{}";
            $language = "{}";
            $direction = "{}";
            $duration = {};
            $hints = "{}";
            
            UPDATE `users`
            SET session_id = $session_id
            WHERE chat_id == $chat_id;
            
            UPSERT INTO `training_session_info`
            (`chat_id`, `session_id`, `strategy`, `language`, `direction`, `duration`, `hints`) VALUES
            ($chat_id, $session_id, $strategy, $language, $direction, $duration, $hints)
            """.format(
                chat_id, session_info["session_id"],
                session_info["strategy"], session_info["language"],
                session_info["direction"], session_info["duration"], session_info["hints"]
            ),
            commit_tx=True,
        )

    return pool.retry_operation_sync(callee)


def get_session_info(pool, chat_id, session_id):
    def callee(session):
        result_sets = session.transaction().execute(
            """
            SELECT *
            FROM `{}`
            WHERE chat_id == {} AND session_id == {}
            """.format(
                TRAINING_SESSIONS_INFO_TABLE_PATH, chat_id, session_id
            ),
            commit_tx=True,
        )
        return result_sets[0].rows[0]

    return pool.retry_operation_sync(callee)

def create_training_session(pool, chat_id, session_info):
    def callee(session):
        session.transaction().execute(
            """
            $session_id = {};
            $chat_id = {};
            $language = "{}";
            $length = {};
            $strategy = "{}";
            $order = "{}";
            
            $words_sample = (
                SELECT
                    $chat_id AS chat_id,
                    $session_id AS session_id,
                    word,
                    translation,
                    ROW_NUMBER() OVER w AS word_idx,
                FROM `{}`
                WHERE
                    chat_id == $chat_id
                    AND language == $language
                    AND CASE
                        WHEN $strategy == "new" AND $order == "to"
                            THEN NVL(n_trains_to, 0) <= 2
                        WHEN $strategy == "new" AND $order == "from"
                            THEN NVL(n_trains_from, 0) <= 2
                        WHEN $strategy == "bad" AND $order == "to"
                            THEN n_trains_to >= 1 AND 1.0 * score_to / n_trains_to <= 0.7
                        WHEN $strategy == "bad" AND $order == "from"
                            THEN n_trains_from >= 1 AND 1.0 * score_from / n_trains_from <= 0.7
                        ELSE True
                    END
                WINDOW w AS (
                    ORDER BY RandomNumber(CAST($session_id AS String) || word)
                )
            );

            UPSERT INTO `{}`
            SELECT * FROM $words_sample
            WHERE word_idx <= $length;
            """.format(
                session_info["session_id"], chat_id, session_info["language"], session_info["duration"],
                session_info["strategy"], session_info["direction"],
                VOCABS_TABLE_PATH, TRAINING_SESSIONS_TABLE_PATH
            ),
            commit_tx=True,
        )

    return pool.retry_operation_sync(callee)


def create_group_training_session(pool, chat_id, session_info):
    def callee(session):
        session.transaction().execute(
            """
            $session_id = {};
            $chat_id = {};
            $language = "{}";
            $length = {};
            $group_id = "{}";
            
            $words_sample = (
                SELECT
                    $chat_id AS chat_id,
                    $session_id AS session_id,
                    v.word AS word,
                    v.translation AS translation,
                    ROW_NUMBER() OVER w AS word_idx,
                FROM `{}` AS v
                INNER JOIN `{}` AS g USING (chat_id, language, word)
                WHERE
                    v.chat_id == $chat_id
                    AND v.language == $language
                    AND g.group_id == $group_id
                WINDOW w AS (
                    ORDER BY RandomNumber(CAST($session_id AS String) || v.word)
                )
            );

            UPSERT INTO `{}`
            SELECT * FROM $words_sample
            WHERE word_idx <= $length;
            """.format(
                session_info["session_id"], chat_id, session_info["language"],
                session_info["duration"], session_info["group_id"],
                VOCABS_TABLE_PATH, GROUPS_CONTENTS_TABLE_PATH, TRAINING_SESSIONS_TABLE_PATH
            ),
            commit_tx=True,
        )

    return pool.retry_operation_sync(callee)


def get_training_words(pool, chat_id, session_info):
    def callee(session):
        result_sets = session.transaction().execute(
            """
            $session_id = {};
            $chat_id = {};

            SELECT * FROM `{}`
            WHERE
                session_id == $session_id
                AND chat_id == $chat_id
            ORDER BY word_idx;
            """.format(
                session_info["session_id"], chat_id,
                TRAINING_SESSIONS_TABLE_PATH
            ),
            commit_tx=True,
        )
        return result_sets[0].rows

    return pool.retry_operation_sync(callee)


def set_training_scores(pool, chat_id, session_id, word_idxs, scores):
    def callee(session):
        session.transaction().execute(
            """
            $chat_id = {};
            $session_id = {};
            $word_idxs = {};
            $scores = {};

            $new_scores = (
                SELECT
                    $chat_id AS chat_id,
                    $session_id AS session_id,
                    ListZip($word_idxs, $scores) AS scores,
            );

            UPSERT INTO `{}`
            SELECT
                chat_id,
                session_id,
                scores.0 AS word_idx,
                scores.1 AS score,
            FROM $new_scores
            FLATTEN LIST BY scores
            """.format(
                chat_id, session_id, json.dumps(word_idxs), json.dumps(scores),
                TRAINING_SESSIONS_TABLE_PATH
            ),
            commit_tx=True,
        )

    return pool.retry_operation_sync(callee)


def update_final_scores(pool, chat_id, session_info):
    def callee(session):
        session.transaction().execute(
            """
            $chat_id = {};
            $session_id = {};
            $language = "{}";
            $order = "{}";

            $format_dttm = DateTime::Format("%Y-%m-%d %H:%M:%S");
            $get_dttm = ($session_id) -> (
                $format_dttm(DateTime::FromSeconds(
                    CAST($session_id AS Uint32)
                ))
            );

            $current_words = (
                SELECT
                    word,
                    score,
                FROM `training_sessions`
                WHERE
                    chat_id == $chat_id
                    AND session_id == $session_id
            );

            $new_scores = (
                SELECT
                    v.*,
                    IF($order == "to", $get_dttm($session_id), v.last_train_to) AS last_train_to,
                    IF($order == "from", $get_dttm($session_id), v.last_train_from) AS last_train_from,
                    IF($order == "to", NVL(v.n_trains_to, 0) + 1, v.n_trains_to) AS n_trains_to,
                    IF($order == "from", NVL(v.n_trains_from, 0) + 1, v.n_trains_from) AS n_trains_from,
                    IF($order == "to", NVL(v.score_to, 0) + 1, v.score_to) AS score_to,
                    IF($order == "from", NVL(v.score_from, 0) + 1, v.score_from) AS score_from,
                WITHOUT
                    v.last_train_from,
                    v.last_train_to,
                    v.n_trains_from,
                    v.n_trains_to,
                    v.score_from,
                    v.score_to
                FROM `vocabularies` AS v
                INNER JOIN $current_words AS cw ON v.word == cw.word
                WHERE
                    v.chat_id == $chat_id
                    AND v.language == $language
            );

            UPDATE `vocabularies` ON
            SELECT * FROM $new_scores;

            UPDATE `users`
            SET session_id = NULL
            WHERE chat_id == $chat_id;
            """.format(
                chat_id, session_info["session_id"], session_info["language"], session_info["direction"]
            ),
            commit_tx=True,
        )

    return pool.retry_operation_sync(callee)


def get_group_by_name(pool, chat_id, language, group_name):
    def callee(session):
        result_sets = session.transaction().execute(
            """    
            SELECT group_id, group_name, is_creator FROM `{}`
            WHERE
                chat_id == {}
                AND language == '{}'
                AND group_name == '{}'
            """.format(
                GROUPS_TABLE_PATH, chat_id, language, group_name
            ),
            commit_tx=True,
        )
        return result_sets[0].rows

    return pool.retry_operation_sync(callee)


def add_group(pool, chat_id, language, group_name, group_id, is_creator):
    def callee(session):
        session.transaction().execute(
            """    
            INSERT INTO `{}` (chat_id, language, group_id, group_name, is_creator) VALUES
                ({}, '{}', '{}', '{}', {});
            """.format(
                GROUPS_TABLE_PATH, chat_id, language,
                group_id, group_name, is_creator
            ),
            commit_tx=True,
        )

    return pool.retry_operation_sync(callee)


def get_all_groups(pool, chat_id, language):
    def callee(session):
        result_sets = session.transaction().execute(
            """    
            SELECT group_name, group_id FROM `{}`
            WHERE
                chat_id == {}
                AND language == '{}'
            """.format(
                GROUPS_TABLE_PATH, chat_id, language
            ),
            commit_tx=True,
        )
        return result_sets[0].rows

    return pool.retry_operation_sync(callee)


def get_group_contents(pool, group_id):
    def callee(session):
        result_sets = session.transaction().execute(
            """    
            SELECT
                group_contents.word AS word,
                translation,
                score_from,
                score_to,
                n_trains_from,
                n_trains_to,
                added_timestamp,
            FROM `{}` AS group_contents
            INNER JOIN `{}` AS vocabs ON
                group_contents.chat_id == vocabs.chat_id
                AND group_contents.language == vocabs.language
                AND group_contents.word == vocabs.word
            WHERE
                group_contents.group_id == '{}'
            """.format(
                GROUPS_CONTENTS_TABLE_PATH, VOCABS_TABLE_PATH, group_id
            ),
            commit_tx=True,
        )
        return result_sets[0].rows

    return pool.retry_operation_sync(callee)

# TODO: join 2 bulk updates
def bulk_update_group(pool, values):
    def callee(session):
        session.transaction().execute(
            """
            UPSERT INTO `{}` (chat_id, language, group_id, word) VALUES
                {};
            """.format(
                GROUPS_CONTENTS_TABLE_PATH, values
            ),
            commit_tx=True,
        )

    return pool.retry_operation_sync(callee)


def prepare_groups_data(chat_id, language, group_id, words):
    data_list = []
    for word in words:
        data_list.append((
            GROUP_UPDATE_VALUES.format(
                chat_id, language, group_id, word
            )
        ))
    return data_list


def add_words_to_group(pool, chat_id, language, group_id, words):
    data = prepare_groups_data(chat_id, language, group_id, words)
    for i in range(0, len(data), GROUPS_UPDATE_BUCKET_SIZE):
        bulk_update_group(pool, ",\n".join(data[i:i+GROUPS_UPDATE_BUCKET_SIZE]))
