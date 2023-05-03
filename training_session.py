from word import compare_user_input_with_db, get_translation, get_word, get_hint


class TrainingSession:
    def __init__(self, words, order="from", hints="no hints"):
        self.n_words = len(words)
        self.words = iter(words)
        self.scores = dict()
        self.word_counter = 0
        self.order = order
        self.current_info = None
        self.hints = hints

    def process_answer(self, message):
        user_translation = message.text
        real_translation = self.current_info
        word = self.current_info["word"]

        if user_translation == "/stop":
            raise StopIteration

        self.scores[word] = int(compare_user_input_with_db(user_translation, real_translation, self.order))
        return bool(self.scores[word]), get_translation(real_translation, self.order)

    def get_next_pair(self):
        _, self.current_info = next(self.words)
        self.word_counter += 1
        return get_word(self.current_info, self.order), get_hint(self.current_info, self.hints)

