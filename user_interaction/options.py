train_strategy_options = ["random", "new", "bad", "group"]

train_direction_options = {
    "➡️ㅤ": "to",
    "⬅️ㅤ": "from",
}  # invisible symbols to avoid large emoji

train_duration_options = ["10", "20", "All"]

train_hints_options = ["flashcards", "test", "a****z", "no hints"]

train_reactions = {
    0.9: "🎉",
    0.7: "👏",
    0.4: "😐",
    0.0: "😡",
}

show_words_sort_options = [
    "a-z",
    "z-a",
    "score ⬇️",
    "score ⬆️",
    "n trains ⬇️",
    "n trains ⬆️",
    "time added ⬇️",
    "time added ⬆️",
]

add_words_modes = ["one-by-one", "together"]

group_add_words_sort_options = ["a-z", "time added ⬇️"]

group_add_words_prefixes = {
    0: "🖤",
    1: "💚",
}

delete_are_you_sure = {
    "Yes!": True,
    "No..": False,
}

show_languages_mark_current = {
    True: "💚 {}",
    False: "🖤 {}",
}
