import logging
from typing import Any
from functools import wraps
from api.config import configs
import os

LOGGIN_LEVEL = configs.LOGGING_LEVEL


def create_logger(name): 
    logging.basicConfig(format='LOGGER::%(asctime)s::%(name)s.%(funcName)s(line %(lineno)d)::%(levelname)s::%(message)s |')
    logger = logging.getLogger(name)
    logger.setLevel(LOGGIN_LEVEL)
    return logger

    
def get_file_logger(name):
    # Create a custom logger
    logger = logging.getLogger(name)

    # Create handlers
    c_handler = logging.StreamHandler()
    c_handler.setLevel(LOGGIN_LEVEL)

    f_handler = logging.FileHandler('my_logs.log')

    my_format = 'LOGGER::%(asctime)s::%(name)s.%(funcName)s(line %(lineno)d)::%(levelname)s::%(message)s |'
    f_format = logging.Formatter(my_format)
    f_handler.setFormatter(f_format)
    f_handler.setLevel(LOGGIN_LEVEL)

    c_handler.setFormatter(f_format)
    logger.addHandler(f_handler)
    logger.addHandler(c_handler)

    return logger


class Log:

    def __init__(self, name) -> None:
        self.name = name
        self.logger = create_logger(name) 
 

    def __call__(self, fun, *args: Any, **kwds: Any) -> Any:        

        @wraps(fun)
        def wrapper(*args: Any, **kwds: Any):
            self.logger.debug('\n\nOK. -- Функция={} -- args={}'.format(fun.__name__,(args, kwds)))
            res = fun(*args, **kwds)
            self.logger.debug('\n\tРезультат функции {}::{}'.format(fun.__name__, res))
            return res

        wrapper.__name__ = fun.__name__
        return wrapper



@Log(__name__)
def my_fun(x, *args, **kwargs):
    print('locals -- ', locals())
    print('args in my fun::',x)
    return 'my_fun result'


import structlog
import json

class CustomPrintLogger:
    def __init__(self, log_file) -> None:
        self.log_file = log_file
        if not os.path.exists(self.log_file):
            with open(self.log_file,'w') as f:
                ...

    def _dump(self, event_dict:dict):

        event_dict = str(event_dict)
        # event_dict['event'] = str(event_dict['event'])
        try: 
            with open(self.log_file, encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data=[]
        data.append(event_dict)
        data:list
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(data, f)

    def __call__(
        self, logger, name: str, event_dict
    ) -> str | bytes:
        
        self._dump(event_dict)
        return repr(event_dict)

from api.config import configs

def get_struct_logger(name:str, log_file=configs.MAIN_LOG_FILE):
    structlog.configure(processors=[structlog.stdlib.add_log_level, CustomPrintLogger(log_file)])
    log = structlog.get_logger()
    log = log.bind(module=name)
    return log

'''
# HOW TO STRUCT:

log = structlog.get_logger()
files = ['123','456']
for file in files:
    try:
        log = log.bind(file_name=file)
        log.debug('opening the file')
        with open('i do nota exsts') as f:
            f.read()
            raise ValueError('aaaa')
    except Exception as ex:
        log.error(ex)

'''


