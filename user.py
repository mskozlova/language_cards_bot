from collections import defaultdict
import datetime
import json
import random

from training_session import TrainingSession
import word as word_handling


def decode_if_not_none(value):
    return value.decode("utf-8") if value is not None else None


def create_vocabs_from_ydb(ydb_results):
    vocabs = defaultdict(dict)
    for row in ydb_results:
        vocabs[row["language"].decode("utf-8")][row["word"]] = {
            "word": row["word"],
            "translation": json.loads(row["translation"]),
            "history_to": json.loads(row["history_to"]),
            "history_from": json.loads(row["history_from"]),
            "last_train_to": decode_if_not_none(row["last_train_to"]),
            "last_train_from": decode_if_not_none(row["last_train_from"]),
            "score_to": row["score_to"],
            "score_from": row["score_from"],
        }
    return vocabs


class User:
    def __init__(self, chat_id, vocabs=None, current_lang=None, **kwargs):
        if vocabs is None:
            vocabs = dict()
        self.chat_id = chat_id
        self.current_lang = current_lang
        self.vocabs = vocabs
        self.training_session = None
        self.session_strategy = None
        self.session_order = None
        self.session_length = None
        self.session_hints = None

    def set_current_lang(self, language):
        self.current_lang = language

    def get_current_lang(self):
        return self.current_lang

    def get_languages(self):
        return list(self.vocabs.keys())

    def delete_language(self, language):
        if language in self.vocabs:
            del self.vocabs[language]
            self.current_lang = None
            return True
        return False

    def update_vocabulary(self, language, word, translations):
        if language not in self.vocabs:
            self.vocabs[language] = dict()
        word = word.lower().strip()
        translations = [t.lower().strip() for t in translations.split("/")]
        if word not in self.vocabs[language]:
            self.vocabs[language][word] = word_handling.create_new_word(word, translations)
        return len(self.vocabs[language])

    def delete_words(self, language, words):
        if language in self.vocabs:
            for word in words:
                if word in self.vocabs[language]:
                    del self.vocabs[language][word]

    def get_words(self, language):
        if language in self.vocabs:
            return list(self.vocabs[language].keys())

    def update_scores(self, language):
        if self.training_session is not None \
                and self.training_session.n_words == len(self.training_session.scores):
            for word, score in self.training_session.scores.items():
                self.vocabs[language][word]["history_" + self.training_session.order].append(score)
                # TODO: truncate history
                self.vocabs[language][word]["score_" + self.training_session.order] = \
                    word_handling.calculate_score(self.vocabs[language][word],
                                                  self.training_session.order)
                self.vocabs[language][word]["last_train_" + self.training_session.order] = \
                    datetime.datetime.strftime(
                        datetime.datetime.now(),
                        "%Y-%m-%d %H:%M:%S"
                    )
            del self.training_session
            self.training_session = None
            self.session_length = None
            self.session_order = None
            self.session_hints = None
            self.session_strategy = None
            return True
        return False

    def set_session_strategy(self, strategy="random"):
        self.session_strategy = strategy

    def set_session_length(self, n):
        self.session_length = n

    def set_session_order(self, order):
        self.session_order = order

    def set_session_hints(self, hints):
        self.session_hints = hints

    def start_training_session(self, language):
        if language in self.vocabs:
            if self.session_strategy == "random":
                words = random.sample(self.vocabs[language].items(),
                                      max(min(self.session_length, len(self.vocabs[language])), 0))
            elif self.session_strategy == "new":
                new_words = list(filter(lambda x: x[1]["score_" + self.session_order] is None
                                        or x[1]["score_" + self.session_order] <= 2,
                                        self.vocabs[language].items()))
                words = random.sample(
                    new_words,
                    max(min(self.session_length, len(new_words)), 0)
                )
            elif self.session_strategy == "bad":
                bad_words = list(filter(lambda x: x[1]["score_" + self.session_order] is not None
                                        and x[1]["score_" + self.session_order] <= 0.5,
                                        self.vocabs[language].items()))
                words = random.sample(
                    bad_words,
                    max(min(self.session_length, len(bad_words)), 0)
                )
            else:
                # TODO: strategy - old
                words = []

            if self.session_order not in ("to", "from"):
                words = []
            self.training_session = TrainingSession(words, self.session_order, self.session_hints)

    def get_language_info(self, language):
        pass
