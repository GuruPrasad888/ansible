import json
import os

import CoreCode.logger as Logger
import Definitions.system_definitions as SystemDefinitions
import Definitions.message_definitions as MessageDefinitions



class ConfigurationManager():
    def __init__(self):
        self.__logger = Logger.get_logger(logger_name=__name__)
        self.__logger.info("ConfigurationManager initializer start")

        if os.path.exists(SystemDefinitions.CONFIGURATION_FILE_PATH) and os.path.isfile(SystemDefinitions.CONFIGURATION_FILE_PATH):
            try:
                with open(SystemDefinitions.CONFIGURATION_FILE_PATH, SystemDefinitions.FILE_READ_MODE) as configuration_file:
                    self.__configuration_dictionary = json.load(configuration_file)
            except Exception as exception:
                self.__logger.error("Failed to get configuration data: {}".format(exception))
        else:
            self.__logger.error("Configuration File not found")

        self.__logger.info("ConfigurationManager initializer end")


    def get_postgres_configuration(self):
        if SystemDefinitions.POSTGRES_CONFIGURATION_KEY in self.__configuration_dictionary:
            if self.__configuration_dictionary[SystemDefinitions.POSTGRES_CONFIGURATION_KEY] != {}:
                postgres_configuration = self.__configuration_dictionary[SystemDefinitions.POSTGRES_CONFIGURATION_KEY]
        else:
            self.__logger.error("Configuration.json file does not contain postgres configuration")

        return postgres_configuration
    

    def get_redis_configuration(self):
        if SystemDefinitions.REDIS_CONFIGURATION_KEY in self.__configuration_dictionary:
            if self.__configuration_dictionary[SystemDefinitions.REDIS_CONFIGURATION_KEY] != {}:
                redis_configuration = self.__configuration_dictionary[SystemDefinitions.REDIS_CONFIGURATION_KEY]
        else:
            self.__logger.error("Configuration.json file does not contain redis configuration")

        return redis_configuration
    

    def get_base_directory(self):
        if SystemDefinitions.BASE_DIRECTORY_KEY in self.__configuration_dictionary:
            if self.__configuration_dictionary[SystemDefinitions.BASE_DIRECTORY_KEY] != "":
                base_directory = self.__configuration_dictionary[SystemDefinitions.BASE_DIRECTORY_KEY]
        else:
            self.__logger.error("Configuration.json file does not contain  base directory")

        return base_directory