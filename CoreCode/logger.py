import logging
import logging.handlers
import os


LOG_DIRECTORY = 'LogFiles'

DEFAULT_LOG_FILE = 'Ansible.log'
DEFAULT_FILE_OPEN_MODE = 'a'   # Append mode
DEFAULT_LOG_LEVEL = logging.DEBUG  # Debug Log level
SYSLOG_ADDRESS_DIR = "/dev/log"


def get_logger(logger_name,
               log_filename=DEFAULT_LOG_FILE,
               file_open_mode=DEFAULT_FILE_OPEN_MODE,
               logger_level=DEFAULT_LOG_LEVEL,
               file_log_enable=True,
               stdout_log_enable=False,
               syslog_enable=False):
    """
        This function returns a logger object, use the object's appropriate methods like info(), debug(), error(), critical(), exception() to log your message
        based on the severity of the message.
        Args    - logger_name : logger name must be unique for every module in which the logger object is used. Pass __name__ as the argument to avoid confusion,
                  log_filename : Filename to which the log content must be written. Default file is CPEApplication.log [LogFiles/CPEApplication.log],
                  file_open_mode : Open Logfile in write/append/ mode. Default mode is append mode,
                  logger_level : Logging severity level. Default logging level is DEBUG,
                  file_log_enable : True if you want to write log message to a file. Default value is True
                  stdout_log_enable : True if you want to display log messages in standard out console. Default value is True
        Returns - logger object
        Raises  - None
    """

    file_and_stdout_formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(filename)s | %(lineno)d | %(module)s | %(funcName)s | %(message)s')
    syslog_formatter = logging.Formatter('chiefnet | %(levelname)s | %(filename)s | %(lineno)d | %(module)s | %(funcName)s | %(message)s')

    logger = logging.getLogger(logger_name)
    logger.setLevel(logger_level)

    if stdout_log_enable == True:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(file_and_stdout_formatter)
        logger.addHandler(stream_handler)

    if syslog_enable == True:
        syslog_handler = logging.handlers.SysLogHandler(address=SYSLOG_ADDRESS_DIR)
        syslog_handler.formatter = syslog_formatter
        logger.addHandler(syslog_handler)

    if file_log_enable == True:
        if not os.path.exists(LOG_DIRECTORY):
            os.makedirs(LOG_DIRECTORY + os.path.sep)

        log_file_path = LOG_DIRECTORY + os.path.sep + log_filename

        file_handler = logging.FileHandler(log_file_path, mode=file_open_mode)
        file_handler.setFormatter(file_and_stdout_formatter)
        logger.addHandler(file_handler)

    return logger
