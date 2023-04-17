import queue
from functools import wraps
from flask import request

log_queue = queue.Queue()

class Log:
    def __init__(self, room_id):
        self.room_id = room_id
    
    def log(self, msg):
        log_queue.put((msg, self.room_id))

def get_socket_log():
    return Log(request.sid)

def with_logging(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_socket_log()
        logger.log(f"invoke {func.__name__}...")
        result = func(*args, **kwargs, logger = logger)
        logger.log(f"{func.__name__} completed.")
        return result
    return wrapper