from telebot import types


empty_markup = types.ReplyKeyboardRemove()


def get_reply_keyboard(options, additional=None):
    markup = types.ReplyKeyboardMarkup(
        row_width=len(options),
        resize_keyboard=True,
        one_time_keyboard=True
    )
    markup.add(*options, row_width=len(options))
    if additional:
        markup.add(*additional, row_width=len(options))

    return markup
