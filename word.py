import json


def ifnull(x, replace):
    if x is None:
        return replace
    return x


def get_translation_pretty(db):
    return "/".join(json.loads(db["translation"]))


def get_word(info, order="from"):
    if order == "from":
        return info["word"]
    elif order == "to":
        return get_translation_pretty(info)


def get_translation(info, order="from"):
    if order == "from":
        return get_translation_pretty(info)
    elif order == "to":
        return info["word"]


def get_hint(info, order="from", hint="no hints"):
    if hint == "no hints":
        return None
    if hint == "a****z":
        translation = get_translation(info, order)
        translation = translation.split("/")[0]
        if len(translation) <= 2:
            return "*" * len(translation)
        return translation[0] + "*" * (len(translation) - 2) + translation[-1]
    if hint == "test":
        pass


def compare_user_input_with_db(user_input, db, hints_type=None, order="from"):
    if hints_type == "flashcards":
        return True
    if order == "from":
        return any(t == user_input.lower().strip() for t in json.loads(db["translation"]))
    elif order == "to":
        return (user_input.lower().strip() == db["word"])


def get_overall_score(db):
    if db["score_to"] is None and db["score_from"] is None:
        return None
    
    if db["score_to"] is None:
        return db["score_from"] / db["n_trains_from"]
    
    if db["score_from"] is None:
        return db["score_to"] / db["n_trains_to"]
    
    return 1 / 2 * db["score_from"] / db["n_trains_from"] + \
        1 / 2 * db["score_to"] / db["n_trains_to"]


def get_total_trains(db):
    return ifnull(db["n_trains_from"], 0) + ifnull(db["n_trains_to"], 0)


def get_reaction_to_score(score):
    if score is None:
        return "🖤"
    if score < 0.2:
        return "💔"
    if score < 0.5:
        return "❤️"
    if score < 0.7:
        return "🧡"
    if score < 0.85:
        return "💛"
    return "💚"


def format_word_for_listing(db):
    if db["score"] is None:
        return "{}` ???? {:>4}  {} - {}`".format(
            get_reaction_to_score(db["score"]),
            db["n_trains"],
            db["word"],
            "/".join(json.loads(db["translation"]))
        )
        
    return "{}` {:>3}% {:>4}  {} - {}`".format(
        get_reaction_to_score(db["score"]),
        int(db["score"] * 100),
        db["n_trains"],
        db["word"],
        "/".join(json.loads(db["translation"]))
    )


def format_word_for_group_action(db):
    return "{} - {}".format(json.loads(db["translation"])[0], db["word"])


def get_word_from_group_action(word):
    return word.split(" - ")[1]


class Word:
    def __init__(self, db_entry):
        self.db_entry = db_entry
    
    
    def get_score(self, score_type):
        assert score_type in ("from", "to"), "score_type should be one of ('from', 'to')"
        if self.db_entry[f"score_{score_type}"] is None:
            return None
        return self.db_entry[f"score_{score_type}"] / self.db_entry[f"n_trains_{score_type}"]
    
    
    def get_overall_score(self):
        score_to = self.get_score("to")
        score_from = self.get_score("from")
        
        if score_to is None and score_from is None:
            return None
    
        if score_to is None:
            return score_from
        
        if score_from is None:
            return score_to
        
        return (score_to + score_from) / 2
    
    def get_total_trains(self):
        return ifnull(self.db_entry["n_trains_from"], 0) + ifnull(self.db_entry["n_trains_to"], 0)
