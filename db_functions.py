import datetime
import json

import ydb


USERS_TABLE_PATH = "users"
VOCABS_TABLE_PATH = "vocabularies"
TRAINING_SESSIONS_TABLE_PATH = "training_sessions"
TRAINING_SESSIONS_INFO_TABLE_PATH = "training_session_info"
WORDS_UPDATE_BUCKET_SIZE = 20

VOCABS_UPDATE_VALUES = "(CAST({} AS Uint64), '{}', CAST('{}' AS Utf8), " \
                       "{}, {}, CAST({} AS Float), CAST({} AS Float), " \
                       "CAST('{}' AS Utf8))"


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


def update_user(pool, user):
    def callee(session):
        session.transaction().execute(
            """
            UPSERT INTO `{}` (chat_id, current_lang, languages) VALUES
                ({}, '{}', '{}');
            """.format(
                USERS_TABLE_PATH, user.chat_id, user.current_lang,
                json.dumps(list(user.vocabs.keys()), ensure_ascii=False)
            ),
            commit_tx=True,
        )

    return pool.retry_operation_sync(callee)


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
                score_from, score_to, translation) VALUES
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
                translation
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
                translation,
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


def get_current_session_id(pool, chat_id):
    def callee(session):
        result_sets = session.transaction().execute(
            """
            SELECT session_id
            FROM `{}`
            WHERE chat_id == {}
            """.format(
                USERS_TABLE_PATH, chat_id
            ),
            commit_tx=True,
        )
        raw_result = result_sets[0].rows
        return raw_result[0]["session_id"] if len(raw_result) == 1 else None

    return pool.retry_operation_sync(callee)


def init_training_session(pool, chat_id, language, session_id, strategy):
    def callee(session):
        session.transaction().execute(
            """
            $chat_id = {};
            $session_id = {};
            $strategy = "{}";
            $language = "{}";
            
            UPDATE `users`
            SET session_id = $session_id
            WHERE chat_id == $chat_id;
            
            UPSERT INTO `training_session_info` (`chat_id`, `session_id`, `strategy`, `language`) VALUES
            ($chat_id, $session_id, $strategy, $language)
            """.format(
                chat_id, session_id, strategy, language
            ),
            commit_tx=True,
        )

    return pool.retry_operation_sync(callee)


def set_session_order_and_length(pool, chat_id, session_id, order, length):
    def callee(session):
        session.transaction().execute(
            """
            UPDATE `{}`
            SET order = "{}", length = {}
            WHERE chat_id == {} AND session_id == {};
            """.format(
                TRAINING_SESSIONS_INFO_TABLE_PATH, order, length, chat_id, session_id
            ),
            commit_tx=True,
        )

    return pool.retry_operation_sync(callee)


def set_session_hints(pool, chat_id, session_id, hints):
    def callee(session):
        session.transaction().execute(
            """
            UPDATE `{}`
            SET hints = "{}", current_word_idx = 1
            WHERE session_id == {} AND chat_id == {};
            """.format(
                TRAINING_SESSIONS_INFO_TABLE_PATH, hints, session_id, chat_id
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


def create_training_session(pool, chat_id, session_id, current_lang, length, strategy, order):
    def callee(session):
        session.transaction().execute(
            """
            $session_id = {};
            $chat_id = {};
            $language = "{}";
            $length = {};
            $strategy = "{}";
            $order = "{}";

            UPSERT INTO `training_sessions`
            SELECT
                $chat_id AS chat_id,
                $session_id AS session_id,
                word,
                ROW_NUMBER() OVER w AS word_idx,
            FROM `vocabularies`
            WHERE
                chat_id == $chat_id
                AND language == $language
                AND CASE
                    WHEN $strategy == "new" AND $order == "to"
                        THEN NVL(n_trains_to, 0) <= 2
                    WHEN $strategy == "new" AND $order == "from"
                        THEN NVL(n_trains_from, 0) <= 2
                    WHEN $strategy == "bad" AND $order == "to"
                        THEN score_to <= 0.7
                    WHEN $strategy == "bad" AND $order == "from"
                        THEN score_from <= 0.7
                    ELSE True
                END
            WINDOW w AS (
                ORDER BY RandomNumber(CAST($session_id AS String) || word)
            )
            LIMIT $length;
            """.format(
                session_id, chat_id, current_lang, length, strategy, order
            ),
            commit_tx=True,
        )

    return pool.retry_operation_sync(callee)


def update_length(pool, chat_id, session_id):
    def callee(session):
        session.transaction().execute(
            """
            $chat_id = {};
            $session_id = {};
            
            $length = (
                SELECT
                    chat_id,
                    session_id,
                    COUNT(*) AS length,
                FROM `training_sessions`
                WHERE chat_id == $chat_id AND session_id == $session_id
                GROUP BY chat_id, session_id
            );
            
            UPDATE `training_session_info` ON
            SELECT * FROM $length;
            """.format(
                chat_id, session_id
            ),
            commit_tx=True,
        )

    return pool.retry_operation_sync(callee)


def get_next_word(pool, chat_id, session_id):
    def callee(session):
        result_sets = session.transaction().execute(
            """
            $chat_id = {};
            $session_id = {};
            
            SELECT
                v.word AS word,
                v.translation AS translation,
                tsi.`order` AS `order`,
                tsi.current_word_idx AS current_word_idx,
                tsi.length AS length,
            FROM `training_session_info` AS tsi
            INNER JOIN `training_sessions` AS ts ON
                tsi.session_id == ts.session_id
                AND tsi.current_word_idx == ts.word_idx
            INNER JOIN `vocabularies` AS v ON
                tsi.language == v.language
                AND ts.word == v.word
            WHERE
                tsi.chat_id == $chat_id
                AND tsi.session_id == $session_id
            """.format(
                chat_id, session_id
            ),
            commit_tx=True,
        )
        return result_sets[0].rows[0]

    return pool.retry_operation_sync(callee)


def get_test_hints(pool, chat_id, session_id, word, language):
    def callee(session):
        result_sets = session.transaction().execute(
            """
            $chat_id = {};
            $session_id = {};
            $word = "{}";
            $language = "{}";
            
            SELECT
                word,
                translation,
                ROW_NUMBER() OVER w AS hint_idx,
            FROM `vocabularies`
            WHERE
                chat_id == $chat_id
                AND language == $language
                AND word != $word
            WINDOW w AS (
                ORDER BY RandomNumber(CAST($session_id AS String) || $word || word)
            )
            LIMIT 3
            """.format(
                chat_id, session_id, word, language
            ),
            commit_tx=True,
        )
        return result_sets[0].rows

    return pool.retry_operation_sync(callee)


def update_score(pool, chat_id, session_id, score):
    def callee(session):
        session.transaction().execute(
            """
            $chat_id = {};
            $session_id = {};
            $score = {};
            
            $update_training_sessions = (
                SELECT
                    chat_id,
                    session_id,
                    current_word_idx AS word_idx,
                    $score AS score,
                FROM `training_session_info`
                WHERE
                    chat_id == $chat_id
                    AND session_id == $session_id
            );
            
            $update_training_session_info = (
                SELECT
                    chat_id,
                    session_id,
                    current_word_idx + 1 AS current_word_idx,
                FROM `training_session_info`
                WHERE
                    chat_id == $chat_id
                    AND session_id == $session_id
            );
            
            UPDATE `training_sessions` ON
            SELECT * FROM $update_training_sessions;
            
            UPDATE `training_session_info` ON
            SELECT * FROM $update_training_session_info;
            """.format(
                chat_id, session_id, score
            ),
            commit_tx=True,
        )

    return pool.retry_operation_sync(callee)


def get_scores(pool, chat_id, session_id):
    def callee(session):
        result_sets = session.transaction().execute(
            """
            SELECT
                COUNT_IF(score IS NOT NULL) AS words,
                SUM(score) AS successes,
            FROM `training_sessions`
            WHERE chat_id == {} AND session_id == {}
            """.format(
                chat_id, session_id,
            ),
            commit_tx=True,
        )
        return result_sets[0].rows[0]

    return pool.retry_operation_sync(callee)


def update_final_scores(pool, chat_id, session_id):
    def callee(session):
        session.transaction().execute(
            """
            $chat_id = {};
            $session_id = {};
            
            $format_dttm = DateTime::Format("%Y-%m-%d %H:%M:%S");
            $get_dttm = ($session_id) -> (
                $format_dttm(DateTime::FromSeconds(
                    CAST($session_id AS Uint32)
                ))
            );
            
            $current_words = (
                SELECT word
                FROM `training_sessions`
                WHERE session_id == $session_id
            );
            
            $all_scores = (
                SELECT
                    cw.word AS word,
                    score,
                    `order`,
                    tsi.language AS language,
                    ts.session_id AS session_id,
                    ROW_NUMBER() OVER w AS recent_idx,
                    COUNT(*) OVER m AS total_trains,
                FROM $current_words AS cw
                INNER JOIN `training_sessions` AS ts ON
                    cw.word == ts.word
                INNER JOIN `training_session_info` AS tsi ON
                    ts.session_id == tsi.session_id
                WHERE score IS NOT NULL
                WINDOW w AS (
                    PARTITION BY ts.word, tsi.`order`, tsi.language
                    ORDER BY ts.session_id DESC
                ), m AS (
                    PARTITION BY ts.word, tsi.`order`, tsi.language
                    ORDER BY ts.session_id DESC
                    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                )
            );
            
            $recent_scores = (
                SELECT
                    language,
                    word,
                    $chat_id AS chat_id,
                    MAX(IF(`order` == "to", $get_dttm(session_id))) AS last_train_to,
                    MAX(IF(`order` == "from", $get_dttm(session_id))) AS last_train_from,
                    MAX(IF(`order` == "to", total_trains)) AS n_trains_to,
                    MAX(IF(`order` == "from", total_trains)) AS n_trains_from,
                    CAST(AVG_IF(score, `order` == "to") AS Float?) AS score_to,
                    CAST(AVG_IF(score, `order` == "from") AS Float?) AS score_from,
                FROM $all_scores
                WHERE recent_idx <= 10
                GROUP BY
                    language,
                    word
            );
            
            UPDATE `vocabularies` ON
            SELECT * FROM $recent_scores;
            
            UPDATE `users`
            SET session_id = NULL
            WHERE chat_id == $chat_id;
            """.format(
                chat_id, session_id
            ),
            commit_tx=True,
        )

    return pool.retry_operation_sync(callee)


def cleanup_scores(pool, chat_id):
    def callee(session):
        session.transaction().execute(
            """
            $chat_id = {};
            
            $to_delete = (
                SELECT
                    ts.chat_id AS chat_id,
                    ts.session_id AS session_id,
                    ts.word_idx AS word_idx,
                FROM `training_sessions` AS ts
                LEFT JOIN `training_session_info` AS tsi USING (chat_id, session_id)
                WHERE
                    ts.chat_id = $chat_id
                    AND (
                        tsi.current_word_idx <= tsi.`length`
                        OR tsi.session_id IS NULL
                    )
            );
            
            DELETE FROM `training_sessions` ON
            SELECT * FROM $to_delete;
            """.format(
                chat_id
            ),
            commit_tx=True,
        )

    return pool.retry_operation_sync(callee)
