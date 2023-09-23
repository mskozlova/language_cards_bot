from telebot.handler_backends import State, StatesGroup
from telebot.storage.base_storage import StateContext, StateStorageBase

import database.model as db_model
from logs import logger

# https://github.com/eternnoir/pyTelegramBotAPI/blob/0f52ca688ffb7af6176d2f73fca92335dc3560eb/telebot/handler_backends.py#L163
# class State:
#     def __init__(self) -> None:
#         self.name = None

#     def __str__(self) -> str:
#         return self.name


# based on Telebot example
# https://github.com/eternnoir/pyTelegramBotAPI/blob/0f52ca688ffb7af6176d2f73fca92335dc3560eb/telebot/storage/redis_storage.py
class StateYDBStorage(StateStorageBase):
    """
    This class is for YDB storage to be used by the bot to track user states.
    """

    def __init__(self, ydb_pool):
        super().__init__()
        self.pool = ydb_pool

    def set_data(self, chat_id, user_id, key, value):
        """
        Set data for a user in a particular chat.
        """
        if db_model.get_state(self.pool, chat_id) is None:
            return False

        full_state = db_model.get_state(self.pool, chat_id)
        data = full_state["data"]
        data[key] = value
        full_state["data"] = data

        db_model.set_state(self.pool, chat_id, full_state)
        return True

    def get_data(self, chat_id, user_id):
        """
        Get data for a user in a particular chat.
        """
        full_state = db_model.get_state(self.pool, chat_id)
        if full_state:
            return full_state.get("data", {})

        return {}

    def set_state(self, chat_id, user_id, state):
        logger.debug(f"SET STATE chat_id: {chat_id}, state: {state}")
        if hasattr(state, "name"):
            state = state.name

        data = self.get_data(chat_id, user_id)
        full_state = {"state": state, "data": data}
        db_model.set_state(self.pool, chat_id, full_state)
        return True

    def delete_state(self, chat_id, user_id):
        """
        Delete state for a particular user.
        """
        if db_model.get_state(self.pool, chat_id) is None:
            return False

        db_model.clear_state(self.pool, chat_id)
        return True

    def reset_data(self, chat_id, user_id):
        """
        Reset data for a particular user in a chat.
        """
        full_state = db_model.get_state(self.pool, chat_id)
        if full_state:
            full_state["data"] = {}
            db_model.set_state(self.pool, chat_id, full_state)
            return True
        return False

    def get_state(self, chat_id, user_id):
        logger.debug(f"GET STATE chat_id: {chat_id}")
        states = db_model.get_state(self.pool, chat_id)
        logger.debug("states: {}".format(states))
        if states is None:
            return None
        logger.debug(
            "GET STATE FINISH {}, type {}".format(
                states.get("state"), type(states.get("state"))
            )
        )
        return states.get("state")

    def get_interactive_data(self, chat_id, user_id):
        return StateContext(self, chat_id, user_id)

    def save(self, chat_id, user_id, data):
        full_state = db_model.get_state(self.pool, chat_id)
        if full_state:
            full_state["data"] = data
            db_model.set_state(self.pool, chat_id, full_state)
            return False


class ForgetMeState(StatesGroup):
    init = State()


class SetLanguageState(StatesGroup):
    init = State()


class AddWordsState(StatesGroup):
    add_words = State()
    translate = State()


class ShowWordsState(StatesGroup):
    choose_sort = State()
    show_words = State()


class DeleteLanguageState(StatesGroup):
    init = State()


class DeleteWordsState(StatesGroup):
    init = State()


class CreateGroupState(StatesGroup):
    init = State()


class DeleteGroupState(StatesGroup):
    select_group = State()
    are_you_sure = State()


class AddGroupWordsState(StatesGroup):
    choose_group = State()
    choose_sorting = State()
    choose_words = State()


class DeleteGroupWordsState(StatesGroup):
    choose_group = State()
    choose_sorting = State()
    choose_words = State()


class ShowGroupsState(StatesGroup):
    init = State()


class TrainState(StatesGroup):
    choose_strategy = State()
    choose_group = State()
    choose_direction = State()
    choose_duration = State()
    choose_hints = State()
    train = State()
