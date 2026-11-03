'''
Module holding LogStore
'''
import logging
import contextlib

from enum    import IntEnum
from typing  import Union
from logging import Logger as StdLogger

# -----------------------------------
class LogLevels(IntEnum):
    '''
    Class meant to symbolize logging levels
    '''
    error   = logging.ERROR
    info    = logging.INFO
    debug   = logging.DEBUG
    verbose = 5
#------------------------------------------------------------
setattr(logging, 'VERBOSE', LogLevels.verbose) # noqa: B010
#------------------------------------------------------------
class Logger(StdLogger):
    def verbose(self, msg, *args, **kwargs):
        if self.isEnabledFor(LogLevels.verbose):
            kwargs.setdefault('stacklevel', 2)
            self._log(LogLevels.verbose, msg, args, **kwargs)

logging.setLoggerClass(Logger)
#------------------------------------------------------------
class StoreFormater(logging.Formatter):
    '''
    Custom formatter
    '''
    LOG_COLORS = {
        logging.VERBOSE : '\033[32m',      # Green # type: ignore
        logging.DEBUG   : '\033[94m',      # Gray
        logging.INFO    : '\033[37m',      # White
        logging.WARNING : '\033[93m',      # Yellow
        logging.ERROR   : '\033[38;5;208m',# Orange
        logging.CRITICAL: '\033[91m'       # Red
    }

    RESET_COLOR = '\033[0m'  # Reset color to default

    def format(self, record):
        log_color = self.LOG_COLORS.get(record.levelno, self.RESET_COLOR)
        message   = super().format(record)

        return f'{log_color}{message}{self.RESET_COLOR}'
#------------------------------------------------------------
class LogStore:
    '''
    Class used to make loggers, set log levels, print loggers, e.g. interface to logging, etc.
    '''
    d_logger      : dict[str,Logger] = {}
    d_levels      : dict[str,   int] = {}
    log_level     = logging.INFO
    is_configured = False
    backend       = 'logging'
    #--------------------------
    @staticmethod
    def level(name : str, lvl : int):
        '''
        Context manager used to set the logging level of a given logger

        Parameters
        ------------------
        name : Name of logger
        lvl  : Integer representing logging level
        '''
        log = LogStore.get_logger(name=name)
        if log is None:
            raise ValueError(f'Cannot find logger {name}')

        old_lvl = log.getEffectiveLevel()

        LogStore.set_level(name, lvl)

        @contextlib.contextmanager
        def _context():
            try:
                yield
            finally:
                LogStore.set_level(name, old_lvl)

        return _context()
    #--------------------------
    @staticmethod
    def get_logger(name : str) -> Union[Logger,None]:
        '''
        Returns logger for a given name or None, if no logger found for that name
        '''
        return LogStore.d_logger.get(name)
    #--------------------------
    @staticmethod
    def add_logger(name : str, exists_ok : bool = False) -> Logger:
        '''
        Will use underlying logging library logging, etc to make logger

        name (str): Name of logger
        '''

        if name in LogStore.d_logger and not exists_ok:
            raise ValueError(f'Logger name {name} already found')

        if name in LogStore.d_logger and     exists_ok:
            print(f'Logger {name} already found, reusing it')
            return LogStore.d_logger[name]

        level  = LogStore.log_level if name not in LogStore.d_levels else LogStore.d_levels[name]

        if   LogStore.backend == 'logging':
            logger = LogStore._get_logging_logger(name, level)
        else:
            raise ValueError(f'Invalid backend: {LogStore.backend}')

        LogStore.d_logger[name] = logger

        return logger
    #--------------------------
    @staticmethod
    def _get_logging_logger(name : str, level : int) -> Logger:
        logger = logging.getLogger(name=name)
        logger.propagate = False

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
    def set_level(name : str, value : int):
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
