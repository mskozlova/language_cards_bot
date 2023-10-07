# Language Cards Bot

This is an implementation of Telegram bot for learning new foreign words.

This code is designed to be run on [Yandex Cloud Serverless Function](https://cloud.yandex.com/en/docs/functions/quickstart/?from=int-console-help-center-or-nav) connected to [YDB database](https://cloud.yandex.com/en/docs/ydb/quickstart?from=int-console-help-center-or-nav) using [TeleBot (pyTelegramBotAPI)](https://pytba.readthedocs.io/en/latest/index.html) python3 package.

## What does the bot do

The bot supports the following:

1. Adding multiple languages to study `/set_language`
2. Adding words and translations `/add_words`
3. Creating word groups within the language `/create_group`
4. Various training modes to help remembering the words `/train`:
    * `flashcards` - the translation is hidden under a spoiler to check yourself
    * `test` - 4 translations to choose an answer from
    * `a***z` - only first and last symbols of the words are shown, the learner has to write the whole word
    * `no hints` - the learner has to write the translation by themselves
5. Tracking the progress: no hints trainings produce scores for words `/show_words`
6. Choosing a specific subset of words to study
    * random words
    * newly added words - words with small number of trainings
    * words with low scores
    * words from a specific group
7. Deleting all user information from the database `/forget_me`

## How to set up an instance of the bot
TBD