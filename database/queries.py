USERS_TABLE_PATH = "users"
VOCABS_TABLE_PATH = "vocabularies"
GROUPS_TABLE_PATH = "groups"
GROUPS_CONTENTS_TABLE_PATH = "group_contents"
LANGUAGES_TABLE_PATH = "languages"
TRAINING_SESSIONS_TABLE_PATH = "training_sessions"
TRAINING_SESSIONS_INFO_TABLE_PATH = "training_session_info"
STATES_TABLE_PATH = "user_states"
    

# Manage tables queries
truncate_tables_queries = [
    """
    DELETE FROM `{}` ON SELECT * FROM `{}`
    """.format(table_name, table_name)
    for table_name in [
        USERS_TABLE_PATH,
        VOCABS_TABLE_PATH,
        GROUPS_TABLE_PATH,
        GROUPS_CONTENTS_TABLE_PATH,
        LANGUAGES_TABLE_PATH,
        TRAINING_SESSIONS_TABLE_PATH,
        TRAINING_SESSIONS_INFO_TABLE_PATH,
        STATES_TABLE_PATH,
    ]
]

# Data manipulation queries
create_user = f"""
    DECLARE $chat_id AS Int64;

    INSERT INTO `{USERS_TABLE_PATH}` (chat_id) VALUES ($chat_id);
"""

get_user_info = f"""
    DECLARE $chat_id AS Int64;
    
    SELECT * FROM `{USERS_TABLE_PATH}`
    WHERE chat_id == $chat_id;
"""

get_user_state = f"""
    DECLARE $chat_id AS Int64;

    SELECT state
    FROM `{STATES_TABLE_PATH}`
    WHERE chat_id == $chat_id;
"""

set_user_state = f"""
    DECLARE $chat_id AS Int64;
    DECLARE $state AS Utf8?;

    UPSERT INTO `{STATES_TABLE_PATH}` (`chat_id`, `state`) VALUES
        ($chat_id, $state);
"""

delete_user = f"""
    DECLARE $chat_id AS Int64;

    $groups = (
        SELECT group_id
        FROM `{GROUPS_TABLE_PATH}`
        WHERE
            chat_id == $chat_id
            AND is_creator
    );

    DELETE FROM `{VOCABS_TABLE_PATH}`
    WHERE chat_id == $chat_id;

    DELETE FROM `{USERS_TABLE_PATH}`
    WHERE chat_id == $chat_id;

    DELETE FROM `{LANGUAGES_TABLE_PATH}`
    WHERE chat_id == $chat_id;

    DELETE FROM `{TRAINING_SESSIONS_INFO_TABLE_PATH}`
    WHERE chat_id == $chat_id;

    DELETE FROM `{TRAINING_SESSIONS_TABLE_PATH}`
    WHERE chat_id == $chat_id;
    
    DELETE FROM `{STATES_TABLE_PATH}`
    WHERE chat_id == $chat_id;

    DELETE FROM `{GROUPS_TABLE_PATH}`
    WHERE
        chat_id == $chat_id
        OR group_id IN $groups;
        
    DELETE FROM `{GROUPS_CONTENTS_TABLE_PATH}`
    WHERE
        chat_id == $chat_id
        OR group_id IN $groups;
"""

delete_language = f"""
    DECLARE $chat_id AS Int64;
    DECLARE $language AS String;

    $groups = (
        SELECT group_id
        FROM `{GROUPS_TABLE_PATH}`
        WHERE
            chat_id == $chat_id
            AND language == $language
            AND is_creator
    );
    $sessions = (
        SELECT session_id
        FROM `{TRAINING_SESSIONS_INFO_TABLE_PATH}`
        WHERE
            chat_id == $chat_id
            AND language == $language
    );

    DELETE FROM `{VOCABS_TABLE_PATH}`
    WHERE
        chat_id == $chat_id
        AND language == $language;
        
    UPDATE `{USERS_TABLE_PATH}`
    SET current_lang = NULL
    WHERE chat_id == $chat_id;

    DELETE FROM `{LANGUAGES_TABLE_PATH}`
    WHERE
        chat_id == $chat_id
        AND language == $language;

    DELETE FROM `{TRAINING_SESSIONS_INFO_TABLE_PATH}`
    WHERE
        chat_id == $chat_id
        AND language == $language;

    DELETE FROM `{TRAINING_SESSIONS_TABLE_PATH}`
    WHERE
        chat_id == $chat_id
        AND session_id IN $sessions;

    DELETE FROM `{GROUPS_TABLE_PATH}`
    WHERE
        (
            chat_id == $chat_id
            AND language == $language
        )
        OR group_id IN $groups;
        
    DELETE FROM `{GROUPS_CONTENTS_TABLE_PATH}`
    WHERE
        (
            chat_id == $chat_id
            AND language == $language
        )
        OR group_id IN $groups;
"""

get_user_vocabs = f"""
    DECLARE $chat_id AS Int64;
    
    SELECT * FROM `{VOCABS_TABLE_PATH}`
    WHERE chat_id == $chat_id
"""

get_full_vocab = f"""
    DECLARE $chat_id AS Int64;
    DECLARE $language AS String;
    
    SELECT
        word,
        score_from,
        score_to,
        n_trains_from,
        n_trains_to,
        translation,
        added_timestamp,
    FROM `{VOCABS_TABLE_PATH}`
    WHERE
        chat_id == $chat_id
        AND language == $language
"""

get_words_from_vocab = f"""
    DECLARE $chat_id AS Int64;
    DECLARE $language AS String;
    DECLARE $words AS List<Utf8>;
     
    SELECT word FROM `{VOCABS_TABLE_PATH}`
    WHERE
        chat_id == $chat_id
        AND language == $language
        AND word IN $words
"""

delete_words_from_vocab = f"""
    DECLARE $chat_id AS Int64;
    DECLARE $language AS String;
    DECLARE $words AS List<Utf8>;
     
    DELETE FROM `{VOCABS_TABLE_PATH}`
    WHERE
        chat_id == $chat_id
        AND language == $language
        AND word IN $words
"""

update_current_lang = f"""
    DECLARE $chat_id AS Int64;
    DECLARE $language AS String;

    UPDATE `{USERS_TABLE_PATH}`
    SET current_lang = $language
    WHERE chat_id == $chat_id;
"""

get_available_languages = f"""
    DECLARE $chat_id AS Int64;

    SELECT language
    FROM `{LANGUAGES_TABLE_PATH}`
    WHERE chat_id == $chat_id
"""

user_add_language = f"""
    DECLARE $chat_id AS Int64;
    DECLARE $language AS Utf8;
    
    INSERT INTO `{LANGUAGES_TABLE_PATH}` (`chat_id`, `language`) VALUES
    ($chat_id, $language)
"""

get_current_language = f"""
    DECLARE $chat_id AS Int64;

    SELECT current_lang
    FROM `{USERS_TABLE_PATH}`
    WHERE chat_id == $chat_id
"""

init_training_session = f"""
    DECLARE $chat_id AS Int64;
    DECLARE $session_id AS Uint64;
    DECLARE $strategy AS String;
    DECLARE $language AS Utf8;
    DECLARE $direction AS String;
    DECLARE $duration AS Uint64;
    DECLARE $hints AS String;

    UPDATE `{USERS_TABLE_PATH}`
    SET session_id = $session_id
    WHERE chat_id == $chat_id;

    UPSERT INTO `{TRAINING_SESSIONS_INFO_TABLE_PATH}`
    (`chat_id`, `session_id`, `strategy`, `language`, `direction`, `duration`, `hints`) VALUES
    ($chat_id, $session_id, $strategy, $language, $direction, $duration, $hints)
"""

get_session_info = f"""
    DECLARE $chat_id AS Int64;
    DECLARE $session_id AS Uint64;
    
    SELECT *
    FROM `{TRAINING_SESSIONS_INFO_TABLE_PATH}`
    WHERE chat_id == $chat_id AND session_id == $session_id
"""

create_training_session = f"""
    DECLARE $chat_id AS Int64;
    DECLARE $session_id AS Uint64;
    DECLARE $language AS Utf8;
    DECLARE $direction AS String;
    DECLARE $duration AS Uint64;
    DECLARE $strategy AS String;

    $words_sample = (
        SELECT
            CAST($chat_id AS Uint64) AS chat_id,
            $session_id AS session_id,
            word,
            translation,
            ROW_NUMBER() OVER w AS word_idx,
        FROM `{VOCABS_TABLE_PATH}`
        WHERE
            chat_id == $chat_id
            AND language == $language
            AND CASE
                WHEN $strategy == "new" AND $direction == "to"
                    THEN NVL(n_trains_to, 0) <= 2
                WHEN $strategy == "new" AND $direction == "from"
                    THEN NVL(n_trains_from, 0) <= 2
                WHEN $strategy == "bad" AND $direction == "to"
                    THEN n_trains_to >= 1 AND 1.0 * score_to / n_trains_to <= 0.7
                WHEN $strategy == "bad" AND $direction == "from"
                    THEN n_trains_from >= 1 AND 1.0 * score_from / n_trains_from <= 0.7
                ELSE True
            END
        WINDOW w AS (
            ORDER BY RandomNumber(CAST($session_id AS String) || word)
        )
    );

    UPSERT INTO `{TRAINING_SESSIONS_TABLE_PATH}`
    SELECT * FROM $words_sample
    WHERE word_idx <= $duration;
"""

create_group_training_session = f"""
    DECLARE $chat_id AS Int64;
    DECLARE $session_id AS Uint64;
    DECLARE $language AS Utf8;
    DECLARE $duration AS Uint64;
    DECLARE $strategy AS String;
    DECLARE $group_id AS String;

    $words_sample = (
        SELECT
            CAST($chat_id AS Uint64) AS chat_id,
            $session_id AS session_id,
            v.word AS word,
            v.translation AS translation,
            ROW_NUMBER() OVER w AS word_idx,
        FROM `{VOCABS_TABLE_PATH}` AS v
        INNER JOIN `{GROUPS_CONTENTS_TABLE_PATH}` AS g USING (chat_id, language, word)
        WHERE
            v.chat_id == $chat_id
            AND v.language == $language
            AND g.group_id == $group_id
        WINDOW w AS (
            ORDER BY RandomNumber(CAST($session_id AS String) || v.word)
        )
    );

    UPSERT INTO `{TRAINING_SESSIONS_TABLE_PATH}`
    SELECT * FROM $words_sample
    WHERE word_idx <= $duration;
"""

get_training_words = f"""
    DECLARE $chat_id AS Int64;
    DECLARE $session_id AS Uint64;

    SELECT * FROM `{TRAINING_SESSIONS_TABLE_PATH}`
    WHERE
        session_id == $session_id
        AND chat_id == $chat_id
    ORDER BY word_idx;
"""

set_training_scores = f"""
    DECLARE $chat_id AS Int64;
    DECLARE $session_id AS Uint64;
    DECLARE $word_idxs AS List<Uint32>;
    DECLARE $scores AS List<Uint32>;

    $new_scores = (
        SELECT
            CAST($chat_id AS Uint64) AS chat_id,
            $session_id AS session_id,
            ListZip($word_idxs, $scores) AS scores,
    );

    UPSERT INTO `{TRAINING_SESSIONS_TABLE_PATH}`
    SELECT
        chat_id,
        session_id,
        scores.0 AS word_idx,
        scores.1 AS score,
    FROM $new_scores
    FLATTEN LIST BY scores
"""

update_final_scores = f"""
    DECLARE $chat_id AS Int64;
    DECLARE $session_id AS Uint64;
    DECLARE $language AS Utf8;
    DECLARE $direction AS String;

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
        FROM `{TRAINING_SESSIONS_TABLE_PATH}`
        WHERE
            chat_id == $chat_id
            AND session_id == $session_id
    );

    $new_scores = (
        SELECT
            v.*,
            IF($direction == "to", $get_dttm($session_id), v.last_train_to) AS last_train_to,
            IF($direction == "from", $get_dttm($session_id), v.last_train_from) AS last_train_from,
            IF($direction == "to", NVL(v.n_trains_to, 0) + 1, v.n_trains_to) AS n_trains_to,
            IF($direction == "from", NVL(v.n_trains_from, 0) + 1, v.n_trains_from) AS n_trains_from,
            IF($direction == "to", NVL(v.score_to, 0) + cw.score, v.score_to) AS score_to,
            IF($direction == "from", NVL(v.score_from, 0) + cw.score, v.score_from) AS score_from,
        WITHOUT
            v.last_train_from,
            v.last_train_to,
            v.n_trains_from,
            v.n_trains_to,
            v.score_from,
            v.score_to
        FROM `{VOCABS_TABLE_PATH}` AS v
        INNER JOIN $current_words AS cw ON v.word == cw.word
        WHERE
            v.chat_id == $chat_id
            AND v.language == $language
    );

    UPDATE `{VOCABS_TABLE_PATH}` ON
    SELECT * FROM $new_scores;

    UPDATE `{USERS_TABLE_PATH}`
    SET session_id = NULL
    WHERE chat_id == $chat_id;
"""

get_group_by_name = f"""
    DECLARE $chat_id AS Int64;
    DECLARE $language AS Utf8;
    DECLARE $group_name AS String;

    SELECT group_id, group_name, is_creator
    FROM `{GROUPS_TABLE_PATH}`
    WHERE
        chat_id == $chat_id
        AND language == $language
        AND group_name == $group_name
"""

add_group = f"""
    DECLARE $chat_id AS Int64;
    DECLARE $language AS Utf8;
    DECLARE $group_id AS String;
    DECLARE $group_name AS String;
    DECLARE $is_creator AS Bool;
    
    INSERT INTO `{GROUPS_TABLE_PATH}`
        (chat_id, language, group_id, group_name, is_creator) VALUES
        ($chat_id, $language, $group_id, $group_name, $is_creator);
"""

delete_group = f"""
    DECLARE $group_id AS String;
    
    DELETE FROM `{GROUPS_CONTENTS_TABLE_PATH}`
    WHERE group_id == $group_id;
    
    DELETE FROM `{GROUPS_TABLE_PATH}`
    WHERE group_id == $group_id;
"""

get_all_groups = f"""
    DECLARE $chat_id AS Int64;
    DECLARE $language AS Utf8;
    
    SELECT group_name, group_id FROM `{GROUPS_TABLE_PATH}`
    WHERE
        chat_id == $chat_id
        AND language == $language
"""

get_group_contents = f"""
    DECLARE $group_id AS String;
    
    SELECT
        group_contents.word AS word,
        translation,
        score_from,
        score_to,
        n_trains_from,
        n_trains_to,
        added_timestamp,
    FROM `{GROUPS_CONTENTS_TABLE_PATH}` AS group_contents
    INNER JOIN `{VOCABS_TABLE_PATH}` AS vocabs ON
        group_contents.chat_id == vocabs.chat_id
        AND group_contents.language == vocabs.language
        AND group_contents.word == vocabs.word
    WHERE
        group_contents.group_id == $group_id
"""

bulk_update_words = f"""
    DECLARE $chat_id AS Int64;
    DECLARE $language AS String;
    DECLARE $words AS List<Utf8>;
    DECLARE $translations AS List<Utf8>;
    DECLARE $added_timestamp AS Uint64;
    
    $update_table = (
        SELECT
            t.*,
            t.word_info.0 AS word,
            t.word_info.1 AS translation,
        WITHOUT t.word_info
        FROM (
            SELECT
                $chat_id AS chat_id,
                $language AS language,
                CAST(NULL AS String?) AS last_train_from,
                CAST(NULL AS String?) AS last_train_to,
                CAST(NULL AS Uint64?) AS score_from,
                CAST(NULL AS Uint64?) AS score_to,
                CAST(NULL AS Uint64?) AS n_trains_from,
                CAST(NULL AS Uint64?) AS n_trains_to,
                $added_timestamp AS added_timestamp,
                ListZip($words, $translations) AS word_info,
        ) AS t
        FLATTEN LIST BY word_info
    );

    UPSERT INTO `vocabularies`
    SELECT * FROM $update_table;
"""

bulk_update_group = f"""
    DECLARE $chat_id AS Int64;
    DECLARE $language AS String;
    DECLARE $group_id AS String;
    DECLARE $words AS List<Utf8>;
    
    $update_table = (
        SELECT *
        FROM (
            SELECT
                $chat_id AS chat_id,
                $language AS language,
                $group_id AS group_id,
                $words AS word
        )
        FLATTEN LIST BY word
    );
    
    UPSERT INTO `{GROUPS_CONTENTS_TABLE_PATH}`
    SELECT * FROM $update_table;
"""

bulk_update_group_delete = f"""
    DECLARE $chat_id AS Int64;
    DECLARE $language AS String;
    DECLARE $group_id AS String;
    DECLARE $words AS List<Utf8>;

    DELETE FROM `{GROUPS_CONTENTS_TABLE_PATH}`
    WHERE
        chat_id == $chat_id
        AND language == $language
        AND group_id == $group_id
        AND word IN $words;
"""
