import json


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
        return any(t == user_input.lower().strip() for t in json.loads(db["translation"])) * 1.0
    elif order == "to":
        return (user_input.lower().strip() == db["word"]) * 1.0


def calculate_score(word, order):
    last_scores = word["history_" + order][-10:]
    return sum(last_scores) / len(last_scores)
