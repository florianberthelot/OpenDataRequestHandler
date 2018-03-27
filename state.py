from threading import Lock


class SingletonState(object):
    __singleton_lock = Lock()
    __singleton_instance = None

    def __init__(self):
        self.__state = "AVAILABLE"

    @classmethod
    def instance(cls):
        if not cls.__singleton_instance:
            with cls.__singleton_lock:
                if not cls.__singleton_instance:
                    cls.__singleton_instance = cls()
        return cls.__singleton_instance

    def get_state(self):
        with self.__singleton_lock:
            return self.__state

    def set_state(self, next_state):
        with self.__singleton_lock:
            self.__state = next_state

    def verify_modify_state(self, verify_state, next_state):
        with self.__singleton_lock:
            if self.__state != verify_state:
                return False
            self.__state = next_state
            return True

    def verify_modify_states(self, verify_states, next_state):
        with self.__singleton_lock:
            is_in = False
            for verify_state in verify_states:
                if self.__state == verify_state:
                    is_in = True
                    break
            if not is_in:
                return False
            self.__state = next_state
            return True
