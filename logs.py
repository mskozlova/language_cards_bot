import logging
from typing import Any
from telebot.types import Message


logging.getLogger().setLevel(logging.DEBUG)


def find_in_args(args, target_type):
    for arg in args:
        if isinstance(arg, target_type):
            return arg


def find_in_kwargs(kwargs, target_type):
    for kwarg in kwargs.values():
        if isinstance(kwarg, target_type):
            return kwarg


def get_message_info(*args, **kwargs):
    chat_id, text = "UNKNOWN", "UNKNOWN"
    
    if find_in_args(args, Message) is not None:
        message = find_in_args(args, Message)
        chat_id, text = message.chat.id, message.text
    elif find_in_kwargs(kwargs, Message) is not None:
        message = find_in_kwargs(args, Message)
        chat_id, text = message.chat.id, message.text  
    
    return chat_id, text


def logged_execution(func):
    def wrapper(*args, **kwargs):
        chat_id, text = get_message_info(*args, **kwargs)

        logging.debug("[LOG] Starting {} - chat_id {} - text {} - args {}, kwargs {}".format(
            func.__name__,
            chat_id, text,
            args, kwargs
        ))
        try:
            func(*args, **kwargs)
            logging.debug("[LOG] Finished {} - chat_id {}".format(func.__name__, chat_id))
        except Exception as e:
            logging.error("[LOG] {} failed - chat_id {} - text {}".format(func.__name__, chat_id, text), exc_info=e)
    return wrapper


class CallbackLogger:
    def __init__(self, func):
        logging.debug("[LOG][CALLBACK] Registered {}".format(func.__name__))
        self.func = func
        
    def __call__(self, *args, **kwargs):
        chat_id, text = get_message_info(*args, **kwargs)
        
        logging.debug("[LOG][CALLBACK] Starting {} - chat_id {} - text {} - args {}, kwargs {}".format(
            self.func.__name__,
            chat_id, text,
            args, kwargs
        ))

        try:
            self.func(*args, **kwargs)
            logging.debug("[LOG][CALLBACK] Finished {} - chat_id {}".format(self.func.__name__, chat_id))
        except Exception as e:
            logging.error("[LOG][CALLBACK] {} failed - chat_id {} - text {}".format(self.func.__name__, chat_id, text), exc_info=e)
