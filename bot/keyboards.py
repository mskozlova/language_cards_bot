from telebot import types

from user_interaction import options, texts
import word as word_utils


empty = types.ReplyKeyboardRemove()


def get_reply_keyboard(options, additional=None, **kwargs):
    if "row_width" in kwargs:
        row_width = kwargs["row_width"]
    else:
        row_width = len(options)
    
    markup = types.ReplyKeyboardMarkup(
        row_width=row_width,
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    markup.add(*options, row_width=row_width)
    if additional:
        markup.add(*additional, row_width=len(additional))

    return markup


def get_masked_choices(choices, mask, additional_commands=[], row_width=2):
    markup = types.ReplyKeyboardMarkup(row_width=row_width, resize_keyboard=True)
        
    formatted_choices = [
        "{}{}".format(
            options.group_add_words_prefixes[mask],
            word_utils.format_word_for_group_action(entry),
        ) for entry, mask in zip(choices, mask)
    ]
    if len(formatted_choices) % row_width != 0:
        formatted_choices.extend([""] * (row_width - len(formatted_choices) % row_width)) 
    
    markup.add(*formatted_choices, row_width=row_width)
    markup.add(*additional_commands, row_width=len(additional_commands))
    return markup
