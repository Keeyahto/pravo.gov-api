from functools import wraps
import time
import requests
import logging

logger = logging.getLogger(__name__)

class BackOff(object):
    def __init__(self, start_sleep_time=0.1, factor=2, border_sleep_time=10):
        self.start_sleep_time = start_sleep_time
        self.sleep_time = 0
        self.factor = factor
        self.border_sleep_time = border_sleep_time
        self.n_of_try = 0
        self.start_time = 0
        self.first_time_error = True

    def __call__(self, function, *args, **kwargs):

        @wraps(function)
        def connector(*args, **kwargs):
            while True:
                try:
                    self.n_of_try += 1
                    res = function(*args, **kwargs)
                    return res
                # except Exception as ex:
                except (requests.exceptions.ConnectionError,
                        requests.exceptions.ReadTimeout) as ex:
                #
                    if self.first_time_error:
                        self.start_time = time.time()
                        self.first_time_error = False
                    if time.time() - self.start_time > self.border_sleep_time:
                        raise ConnectionError('exceeded waiting time')
                    error_message = f'{ex}\nat{function}\n\n RECONNECTING. WAITING TIME:: {self.sleep_time}\n'
                    logger.error(error_message)
                    self.sleep_time = self.start_sleep_time * \
                                      self.factor ** (self.n_of_try)
                    time.sleep(self.sleep_time)
                    logger.error('reconnecting...')

        return connector
