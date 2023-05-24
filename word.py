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


def compare_user_input_with_db(user_input, db, order="from"):
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


def format_word_for_listing(db):
    if db["score"] is None:
        return "`???? {:>4}  {} - {}`".format(
            db["n_trains"],
            db["word"],
            "/".join(json.loads(db["translation"]))
        )
        
    return "`{:>3}% {:>4}  {} - {}`".format(
        int(db["score"] * 100),
        db["n_trains"],
        db["word"],
        "/".join(json.loads(db["translation"]))
    )
