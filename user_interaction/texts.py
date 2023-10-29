# welcome messages
help_message = (
    "Ahoy, sexy! I am a cute little bot for remembering "
    "words you've learned during your language course. Here's how you can use me:\n\n"
    "- /help or /start to read this message again.\n"
    "- /set_language to set current vocabulary "
    "(you can add multiple and switch between them without erasing the progress).\n"
    "- /delete_language to delete current language with all data on words, groups, training sessions.\n"
    "- /add_words to add words to current vocabulary.\n"
    "- /show_words to print out all words you saved for current language.\n"
    "- /delete_words to delete some words from current vocabulary.\n"
    "- /create_group to create new group for words.\n"
    "- /delete_group to delete one of your groups.\n"
    "- /show_groups to show your existing groups for current language.\n"
    "- /group_add_words to add some words from you vocabulary to one of your groups.\n"
    "- /group_delete_words to delete some words from one of your groups.\n"
    "- /train to choose training strategy and start training.\n"
    "- /stop to stop training session without saving the results.\n"
    "- /forget_me to delete all the information I have about you: languages, words, groups, etc."
)

welcome = "Hey! I can see you are new here. Welcome!"

# /forget_me
forget_me_warning = (
    "All your languages, words, training sessions and groups will be deleted without any possibility of recovery.\n\n"
    "Are you sure you want to delete all information the bot has about you?"
)

forget_me_final = (
    "👋 Farewell, my friend! It's sad to see you go.\n"
    "Check /set_language to make sure you're all cleaned up."
)

# /delete_language
delete_language_warning = (
    "You are trying to delete language {}\n\n"
    "All your words, training sessions and groups for this language will be deleted without any possibility of recovery.\n\n"
    "Are you sure you want to delete language?"
)

delete_language_final = (
    "Language {} is deleted.\n"
    "Check /set_language to make sure and to set a new language."
)

# /delete_words
delete_words_start = (
    "Write words to delete. Each word on a new line.\n\n"
    "Use /cancel to exit the process."
)

deleted_words_list = "Deleted {} word(s):\n{}{}"

deleted_words_unknown = "\n\nOther words are unknown."

# language setting
current_language = "Your current language is {}."

no_languages_yet = "You don't have any languages yet."

set_language = "Choose one of your existent languages or create a new one:"

choose_existing_language = "Choose one of you languages or use /new command"

set_language_cancel = "Cancelled setting language!"

new_language_created = "You've created a new language {}."

language_is_set = "Language set: {}.\nYou can /add_words to it or /train"

no_language_is_set = "Language not set. Set in with command /set_language."

create_new_language = (
    "Choose a language you want to learn. Select a flag emoji, for example 🇫🇮.\n"
    "Tip: type a colon ':' and a country code to find an emoji, for example ':fi'.\n\n"
    "If there's no appropriate emoji, write a name as text. Use one word, only latin letters."
)

create_translation_language = (
    "Choose a language you going to translate the words to, usually it's the language you know well.\n"
    "Select a flag emoji, for example 🇬🇧. If there's no appropriate emoji, write a name as text. "
    "Use one word, only latin letters."
)

bad_language_format = "Language should be a flag emoji or one word which consists of latin letters. Try again:"

language_already_exists = "You already have language {}."

# show languages
show_languages_none = "You don't have any languages yet. Try /set_language to add one."

available_languages = "You have {} language(s):\n{}"

# /add_words
add_words_choose_mode = (
    "Choose adding mode:\n"
    "- one-by-one: provide a bunch of words and translate them one by one\n"
    "- together: provide words with translations"
)

add_words_together_instruction = (
    "Write words you want to add as follows:\n\n"
    "first word = only translation\n"
    "second word = translation1 / translation2\n\n"
    "Multiple translations should be separated by '/'.\n"
    "Type /cancel to exit the process."
)

add_words_together_wrong_format = (
    "Entry\n'{}'\nhas wrong format.\n\n" "Try again or type /cancel."
)

add_words_together_empty_word = (
    "Entry\n'{}'\nhas empty word.\n\n" "Try again or type /cancel."
)

add_words_together_empty_translation = (
    "Entry\n'{}'\nhas empty translation.\n\n" "Try again or type /cancel."
)

add_words_instruction_one_by_one_1 = (
    "First, write new words you want to learn, each on new row.\n"
    "For example:\n"
    "hola\n"
    "gracias\n"
    "adiós\n\n"
    "After that I will ask you to provide translations.\n\n"
    "Type /cancel to exit the process."
)

add_words_instruction_one_by_one_2 = (
    "You've added {} words, now let's translate them one by one. "
    "Type /cancel anytime to exit the translation.\n"
    "You can add multiple translations divided by '/', for example:\n"
    "> adiós\n"
    "farewell / goodbye"
)

add_words_finished = "Finished! Saved {} words"

add_words_cancelled = "Cancelled! No words saved."

add_words_none_added = "You didn't add anything. Try again /add_words?"

add_words_translate = "Translate {}"

# /create_group
create_group_name = (
    "Write new group name. It should consist only of latin letters, digits and underscores.\n"
    "For example, 'nouns_type_3'\n"
    "\n"
    "Use /cancel to exit the process."
)

group_name_invalid = "Group name should consist only of latin letters, digits and underscores, try again or /cancel."

group_already_exists = (
    "You already have a group with that name, please try another: /create_group"
)

group_created = "Group is created! Now add some words: /group_add_words"

# sorting
choose_sorting = "Choose sorting:"

sorting_not_supported = "This sorting is not supported. Choose a valid option:"

# misc
exited = "Exited!"

unknown_command_short = "I don't know this command."

unknown_command = "I don't know this command, try again {}"

cancel_short = "Cancelled!"

unknown_message = "I don't know what to do :("

stop_message = "Stopped!"

# show words
words_count = "You have {} word(s) for language '{}'."

no_words_yet = "You don't have any words yet, try /add_words!"

word_formatted = "Page {} of {}:\n\n🤍`    %    #  word`\n{}"

# show_groups
no_groups_yet = "You don't have any groups yet, try /create_group"

group_choose = "Choose one of your groups"

no_such_group = "You don't have a group with that name, choose again."

show_group_done = "Finished group showing!"

show_group_empty = "This group has no words in it yet, try /group_add_words"

# delete_group
group_not_a_creator = "You are not a creator of this group, can't edit or delete it."

delete_group_warning = "Are you sure you want to delete group '{}' for language {}?\nThis will NOT affect words in your vocabulary!"

delete_group_cancel = "Cancelled group deletion!"

delete_group_success = "👍 Group '{}' successfully deleted! /show_groups"

# group_edit
# group_edit_choose = "Select words, page {} of {}."

group_edit_confirm = "✅ㅤ"  # invisible symbol to avoid large emoji

group_edit_choose = "Choose words to {}. Group '{}', page {} out of {}"

group_edit_finished = "Finished!\nEdited group {}: {} {} word(s).\n\n{}"

group_edit_cancelled = "Cancelled! Group was not edited."

group_edit_no_more_words = "That's all the words we have!"

group_edit_unknown_word = "Not a word from the list, ignoring that."

group_edit_full = "There're no more words to add to this group."

group_edit_empty = "There're no words in this group."

# training
training_init = (
    "Choose training strategy.\n"
    "Now available:\n\n"
    "- random - simply random words\n"
    "- new - only words that you've seen not more than 2 times\n"
    "- bad - only words with weak score\n"
    "- group - words from a particular group"
)

training_direction = (
    "Choose training direction: {} ➡️ {}, or {} ⬅️ {}."
)

training_duration = "Choose duration of your training. You can also type in any number."

training_hints = (
    "Choose hints for your training.\n"
    "Training with hints will not affect you word scores. Choose 'no hints' to track your progress."
)

training_strategy_unknown = "This strategy is not supported. Choose a valid strategy:"

training_direction_unknown = (
    "This direction is not supported. Choose a valid direction:"
)

training_duration_unknown = "This duration is not supported. Choose a valid duration:"

training_hints_unknown = "These hints are not supported. Choose valid hints:"

training_no_scores = "Scores are not saved because hints were used."

training_results = "Score: {} / {}\n{} Training complete!\nLet's /train again?"

training_cancelled = "Cancelled training, come back soon and /train again!"

training_stopped = "Session stopped, results not saved.\nLet's /train again?"

training_no_words_found = (
    "There are no words satisfying your parameters, try choosing something else: /train"
)

training_fewer_words = "(I have found fewer words than you have requested)"

training_start = (
    "Starting training.\n" + "Strategy: {}\nDuration: {}\nDirection: {}\nHints: {}{}"
)
training_start_group = "\n\nGroup name: {}"

# train reactions
train_correct_answer = "✅ㅤ"  # invisible symbol to avoid large emoji
train_wrong_answer = "❌ {}"
