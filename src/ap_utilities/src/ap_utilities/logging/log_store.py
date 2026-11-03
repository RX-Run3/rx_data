'''
Module holding LogStore
'''

import logging
import logzero

#------------------------------------------------------------
class StoreFormater(logging.Formatter):
    '''
    Custom formatter
    '''
    LOG_COLORS = {
        logging.DEBUG   : '\033[94m',     # Gray
        logging.INFO    : '\033[37m',     # White
        logging.WARNING : '\033[93m',     # Yellow
        logging.ERROR   : '\033[91m',     # Red
        logging.CRITICAL: '\033[1;91m'    # Bold Red
    }

    RESET_COLOR = '\033[0m'  # Reset color to default

    def format(self, record):
        log_color = self.LOG_COLORS.get(record.levelno, self.RESET_COLOR)
        message   = super().format(record)

        return f'{log_color}{message}{self.RESET_COLOR}'
#------------------------------------------------------------
class LogStore:
    '''
    Class used to make loggers, set log levels, print loggers, e.g. interface to logging/logzero, etc.
    '''
    #pylint: disable = invalid-name
    d_logger      = {}
    d_levels      = {}
    log_level     = logging.INFO
    is_configured = False
    backend       = 'logging'
    #--------------------------
    @staticmethod
    def add_logger(name=None):
        '''
        Will use underlying logging library logzero/logging, etc to make logger

        name (str): Name of logger
        '''

        if   name is None:
            raise ValueError('Logger name missing')

        if name in LogStore.d_logger:
            raise ValueError(f'Logger name {name} already found')

        level  = LogStore.log_level if name not in LogStore.d_levels else LogStore.d_levels[name]

        if   LogStore.backend == 'logging':
            logger = LogStore._get_logging_logger(name, level)
        elif LogStore.backend == 'logzero':
            logger = LogStore._get_logzero_logger(name, level)
        else:
            raise ValueError(f'Invalid backend: {LogStore.backend}')

        LogStore.d_logger[name] = logger

        return logger
    #--------------------------
    @staticmethod
    def _get_logzero_logger(name : str, level : int):
        log = logzero.setup_logger(name=name)
        log.setLevel(level)

        return log
    #--------------------------
    @staticmethod
    def _get_logging_logger(name : str, level : int):
        logger = logging.getLogger(name=name)

        logger.setLevel(level)

        hnd= logging.StreamHandler()
        hnd.setLevel(level)

        fmt= StoreFormater('%(asctime)s - %(filename)s:%(lineno)d - %(message)s', datefmt='%H:%M:%S')
        hnd.setFormatter(fmt)

        if logger.hasHandlers():
            logger.handlers.clear()

        logger.addHandler(hnd)

        return logger
    #--------------------------
    @staticmethod
    def set_level(name, value):
        '''
        Will set the level of a logger, it not present yet, it will store the level and set it when created.
        Parameters:
        -----------------
        name (str): Name of logger
        value (int): 10 debug, 20 info, 30 warning
        '''

        if name in LogStore.d_logger:
            lgr=LogStore.d_logger[name]
            lgr.handlers[0].setLevel(value)
            lgr.setLevel(value)
        else:
            LogStore.d_levels[name] = value
    #--------------------------
    @staticmethod
    def show_loggers():
        '''
        Will print loggers and log levels in two columns
        '''
        print(80 * '-')
        print(f'{"Name":<60}{"Level":<20}')
        print(80 * '-')
        for name, logger in LogStore.d_logger.items():
            print(f'{name:<60}{logger.level:<20}')
    #--------------------------
    @staticmethod
    def set_all_levels(level):
        '''
        Will set all loggers to this level (int)
        '''
        for name, logger in LogStore.d_logger.items():
            logger.setLevel(level)
            print(f'{name:<60}{"->":20}{logger.level:<20}')
#------------------------------------------------------------
