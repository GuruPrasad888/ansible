import os
import yaml

import CoreCode.logger as Logger
from CoreCode.service_manager import ServiceManager

import CoreCode.helper_functions as HelperFunctions

import Definitions.system_definitions as SystemDefinitions
import Definitions.message_definitions as MessageDefinitions
import Definitions.message_code_definitions as MessageCodeDefinitions

LOG_TYPE = "log_type"
LOG_VALUE = "log_value"

INFLUX = "influx"
SYSLOG = "syslog"
SPLUNK = "splunk"

FLUENT_BIT_CONFIGURATION_FILES_BASE_DIRECTORY = "fluent_bit/files"
INFLUXDB_CONFIGURATION_FILE_PATH = "influxdb.conf.j2"
SPLUNK_CONFIGURATION_FILE_PATH = "splunk.conf.j2"
SYSLOG_CONFIGURATION_FILE_PATH = "syslog.conf.j2"

FLUENT_BIT_EXTRAVARS_FILE_NAME = "fluent_bit.yml"

FLUENT_BIT_TASK_FILE_PATH = "fluent_bit/tasks/main.yml"

FLUENT_BIT_PLAYBOOK_NAME = "fluent_bit.yml"

PATH_SEPERATOR_CHARACTER = os.path.sep


class FluentbitManager(ServiceManager):

    def __init__(self, database_manager, status_manager):
        self.__logger = Logger.get_logger(logger_name=__name__)

        self.__logger.info("Fluent Bit manager initializer starts")

        self._database_manager = database_manager
        self._status_manager = status_manager

        self.__influx_configuration_file_path = SystemDefinitions.ROLES_BASE_DIRECTORY + PATH_SEPERATOR_CHARACTER + FLUENT_BIT_CONFIGURATION_FILES_BASE_DIRECTORY + PATH_SEPERATOR_CHARACTER + INFLUXDB_CONFIGURATION_FILE_PATH
        self.__splunk_configuration_file_path = SystemDefinitions.ROLES_BASE_DIRECTORY + PATH_SEPERATOR_CHARACTER + FLUENT_BIT_CONFIGURATION_FILES_BASE_DIRECTORY + PATH_SEPERATOR_CHARACTER + SPLUNK_CONFIGURATION_FILE_PATH
        self.__syslog_configuration_file_path = SystemDefinitions.ROLES_BASE_DIRECTORY + PATH_SEPERATOR_CHARACTER + FLUENT_BIT_CONFIGURATION_FILES_BASE_DIRECTORY + PATH_SEPERATOR_CHARACTER + SYSLOG_CONFIGURATION_FILE_PATH

        self.__task_file_path = SystemDefinitions.ROLES_BASE_DIRECTORY + PATH_SEPERATOR_CHARACTER + FLUENT_BIT_TASK_FILE_PATH
        self.__playbook_path = SystemDefinitions.PLAYBOOKS_BASE_DIRECTORY + PATH_SEPERATOR_CHARACTER + FLUENT_BIT_PLAYBOOK_NAME
        self.__extravars_file_path = SystemDefinitions.EXTRAVARS_BASE_DIRECTORY + PATH_SEPERATOR_CHARACTER + FLUENT_BIT_EXTRAVARS_FILE_NAME

        event_dictionary = {}
        event_dictionary[MessageCodeDefinitions.FLUENT_BIT_EVENT] = self.__configure_fluentbit

        ServiceManager.__init__(self, status_manager= status_manager, event_dictionary=event_dictionary)

        self.__logger.info("Fluent Bit manager initializer ends")


    def __configure_fluentbit(self):
        self.__logger.info("Configure fluent-bit event routine start")

        configuration = self._database_manager.get_fluentbit_configuration(self._message_dictionary[MessageDefinitions.ORGANIZATION_ID_KEY])
        if self.__edit_extravars(configuration=configuration) == True:
                
            if self.__change_source_file_path_in_tasks(configuration=configuration) == True:
                
                ansible_stats = HelperFunctions.run_playbook(playbook_path=self.__playbook_path, extravars_file_path=self.__extravars_file_path, logger_object=self.__logger)

                if ansible_stats == True:
                    if self._status_manager.update_status(message_dictionary = self._message_dictionary, ansible_stats = ansible_stats) == True:
                        return True
                    else:
                        return False
                else:
                    self._status_manager.update_status(message_dictionary = self._message_dictionary, status = False)
                    return False
            else:
                self._status_manager.update_status(message_dictionary = self._message_dictionary, status = False)
                return False
        else:
            self._status_manager.update_status(message_dictionary = self._message_dictionary, status = False)
            return False
        

    def __edit_extravars(self,configuration):
        try:
            type = configuration[LOG_TYPE]
            log_levels_pattern = '|'.join(configuration[LOG_VALUE]["log_levels"])

            with open(self.__extravars_file_path, SystemDefinitions.FILE_READ_MODE) as file:
                content = yaml.safe_load(file)
            
            content["log_levels"] = f"({log_levels_pattern})"

            if type == INFLUX:

                content["influx_domain_name_or_ip"] = configuration[LOG_VALUE]["influx_domain_name_or_ip"]
                content["influx_port"]              = configuration[LOG_VALUE]["influx_port"]
                content["influx_bucket_name"]       = configuration[LOG_VALUE]["influx_bucket_name"]
                content["influx_organization_name"] = configuration[LOG_VALUE]["influx_organization_name"]
                content["influx_token"]             = configuration[LOG_VALUE]["influx_token"]
                content["tls"]                      = configuration[LOG_VALUE]["tls"]

            elif type == SPLUNK:

                content["splunk_host"]          = configuration[LOG_VALUE]["splunk_host"]
                content["splunk_port"]          = configuration[LOG_VALUE]["splunk_port"]
                content["splunk_token"]         = configuration[LOG_VALUE]["splunk_token"]
                content["splunk_send_raw"]      = configuration[LOG_VALUE]["splunk_send_raw"]
                content["splunk_source_type"]   = configuration[LOG_VALUE]["splunk_source_type"]
                content["splunk_index"]         = configuration[LOG_VALUE]["splunk_index"]

            elif type == SYSLOG:

                content["syslog_host"]      = configuration[LOG_VALUE]["syslog_host"]
                content["syslog_port"]      = configuration[LOG_VALUE]["syslog_port"]
                content["syslog_hostname"]  = configuration[LOG_VALUE]["syslog_hostname"]
                content["syslog_appname"]   = configuration[LOG_VALUE]["syslog_appname"]

            else:
                self.__logger.error("Undefined type received: {}".format(type))
                return False

            with open(self.__extravars_file_path, SystemDefinitions.FILE_WRITE_MODE) as file:
                yaml.dump(content, file, default_flow_style=False)

            self.__logger.info("Extravars file updated succcessfully")
            return True

        except Exception as exception:
            self.__logger.error("Error editing extravars file: {}".format(exception))
            return False
    

    def __change_source_file_path_in_tasks(self, configuration):
        try:
            type = configuration[LOG_TYPE]

            if type == INFLUX:
                file_path = self.__influx_configuration_file_path

            elif type == SPLUNK:
                file_path = self.__splunk_configuration_file_path

            elif type == SYSLOG:
                file_path = self.__syslog_configuration_file_path

            with open(self.__task_file_path, SystemDefinitions.FILE_READ_MODE) as file:
                tasks = yaml.safe_load(file)

            for task in tasks:
                if task.get("name") == "Copy the fluent-bit configuration":
                    if "template" in task and "src" in task["template"]:
                        task["template"]["src"] = file_path

            with open(self.__task_file_path, SystemDefinitions.FILE_WRITE_MODE) as file:
                yaml.safe_dump(tasks, file, default_flow_style=False)

            self.__logger.info("Successfully updated the source path to {}".format(file_path))
            return True

        except Exception as exception:
            self.__logger.error("Error updating the source path: {}".format(exception))
            return False
        