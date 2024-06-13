import re
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

CONFIGURATION_FILES_BASE_DIRECTORY = "roles/fluent_bit/files"
INFLUXDB_CONFIGURATION_FILE_PATH = "influxdb.conf"
SPLUNK_CONFIGURATION_FILE_PATH = "splunk.conf"
SYSLOG_CONFIGURATION_FILE_PATH = "syslog.conf"

TASK_FILE_PATH = "roles/fluent_bit/tasks/main.yml"

PLAYBOOK_PATH = "playbooks/fluent_bit.yml"

PATH_SEPERATOR_CHARACTER = os.path.sep



class FluentbitManager(ServiceManager):

    def __init__(self, database_manager, status_manager):
        self.__logger = Logger.get_logger(logger_name=__name__)

        self.__logger.info("Fluent Bit initializer starts")

        self._database_manager = database_manager
        self._status_manager = status_manager

        self.__influx_configuration_file_path = CONFIGURATION_FILES_BASE_DIRECTORY + PATH_SEPERATOR_CHARACTER + INFLUXDB_CONFIGURATION_FILE_PATH
        self.__splunk_configuration_file_path = CONFIGURATION_FILES_BASE_DIRECTORY + PATH_SEPERATOR_CHARACTER + SPLUNK_CONFIGURATION_FILE_PATH
        self.__syslog_configuration_file_path = CONFIGURATION_FILES_BASE_DIRECTORY + PATH_SEPERATOR_CHARACTER + SYSLOG_CONFIGURATION_FILE_PATH

        self.__task_file_path = TASK_FILE_PATH
        self.__playbook_path = PLAYBOOK_PATH

        event_dictionary = {}
        event_dictionary[MessageCodeDefinitions.FLUENT_BIT_INFLUX] = self.__configure_fluentbit

        ServiceManager.__init__(self, status_manager= status_manager, event_dictionary=event_dictionary)

        self.__logger.info("Fluent Bit initializer ends")


    def __configure_fluentbit(self):
        self.__logger.info("Configure fluent-bit event routine start")

        configuration = self._database_manager.get_fluentbit_configuration(self._message_dictionary[MessageDefinitions.ORGANIZATION_ID_KEY])
        type = configuration[LOG_TYPE]
        
        if type == INFLUX:
            if self.__configure_influx(configuration=configuration) == True:
                if self.__change_source_file_path_in_tasks(filepath = self.__influx_configuration_file_path) == True:
                    
                    if self.__run_playbook_and_update_status == True:
                        return True
                    else:
                        return False
                
                else:
                    return False
            else:
                self._status_manager.update_status(message_dictionary = self._message_dictionary, status = False)
                return False
       

        elif type == SYSLOG:
            if self.__configure_syslog(configuration=configuration) == True:
                if self.__change_source_file_path_in_tasks(filepath = self.__syslog_configuration_file_path) == True:
                    
                    if self.__run_playbook_and_update_status == True:
                        return True
                    else:
                        return False
                
                else:
                    return False
            else:
                self._status_manager.update_status(message_dictionary = self._message_dictionary, status = False)
                return False


        elif type == SPLUNK:
            if self.__configure_splunk(configuration=configuration) == True:
                if self.__change_source_file_path_in_tasks(filepath = self.__splunk_configuration_file_path) == True:
                    
                    if self.__run_playbook_and_update_status == True:
                        return True
                    else:
                        return False
                
                else:
                    return False
            else:
                self._status_manager.update_status(message_dictionary = self._message_dictionary, status = False)
                return False


    def __configure_influx(self, configuration):
        try:
            levels_pattern = '|'.join(configuration[LOG_VALUE]["log_levels"])
            filter_section = f"""
[FILTER]
    Name modify
    Match syslog
    Add _hostname {{ ansible_facts['hostname'] }}
    Regex         level ($i)({levels_pattern})
        """
            
            output_section = f"""
[OUTPUT]
    Name          influxdb
    Match         syslog
    Host          {configuration[LOG_VALUE]["influx_domain_name_or_ip"]}
    Port          {configuration[LOG_VALUE]["influx_port"]}
    Bucket        {configuration[LOG_VALUE]["influx_bucket_name"]}
    Org           {configuration[LOG_VALUE]["influx_organization_name"]}
    HTTP_Token    {configuration[LOG_VALUE]["influx_token"]}
    TLS           {configuration[LOG_VALUE]["tls"]}
    Tag_Keys      _hostname
        """
        except Exception as exception:
            self.__logger.error("Error generating influx configuration: {}".format(exception))
            return False

        if self.__rewrite_configurations(filter_section=filter_section, output_section=output_section, file_path=self.__influx_configuration_file_path) == True:
            return True
        else:
            return False

        
    def __configure_syslog(self, configuration):
        try:
            filter_section = self.__generate_filter_configuration(configuration[LOG_VALUE]["log_levels"])

            output_section = f"""
[OUTPUT]
    Name         syslog
    Match        *
    Host         {configuration[LOG_VALUE]['host']}
    Port         {configuration[LOG_VALUE]['port']}
    Mode         tcp
    Syslog_Format rfc5424
        """
            # Append optional parameters if provided
            if configuration[LOG_VALUE]["syslog_hostname"] != None:
                output_section += f"    Syslog_Hostname {configuration[LOG_VALUE]['syslog_hostname']}\n"
            if configuration[LOG_VALUE]["syslog_appname"] != None:
                output_section += f"    Syslog_Appname {configuration[LOG_VALUE]['syslog_appname']}\n"
            
            output_section += "    Syslog_Severity info\n"
        except Exception as exception:
            self.__logger.error("Error generating syslog configuration: {}".format(exception))
            return False

        if self.__rewrite_configurations(filter_section=filter_section, output_section=output_section, file_path=self.__syslog_configuration_file_path) == True:
            return True
        else:
            return False
        

    def __configure_splunk(self, configuration):
        try:
            filter_section = self.__generate_filter_configuration(configuration[LOG_VALUE]["log_levels"])

            output_section = f'''
[OUTPUT]
    Name              splunk
    Match             *
    Host              {configuration[LOG_VALUE]["splunk_host"]}
    Port              {configuration[LOG_VALUE]["splunk_port"]}
    Splunk_Token      {configuration[LOG_VALUE]["splunk_token"]}
    splunk_send_raw   {configuration[LOG_VALUE]["splunk_send_raw"]}
    splunk_sourcetype {configuration[LOG_VALUE]["splunk_source_type"]}
    splunk_index      {configuration[LOG_VALUE]["splunk_index"]}
    tls.verify        Off
        '''
        except Exception as exception:
            self.__logger.error("Error generating influx configuration: {}".format(exception))
            return False

        if self.__rewrite_configurations(filter_section=filter_section, output_section=output_section, file_path=self.__splunk_configuration_file_path) == True:
            return True
        else:
            return False
    

    def __generate_filter_configuration(self, log_levels):
        try:
            levels_pattern = '|'.join(log_levels)

            filter_section = f'''
[FILTER]
    Name         grep
    Match        syslog.*
    Regex        level ($i)({levels_pattern})

[FILTER]
    Name         grep
    Match        openvpn.*
    Regex        level ($i)({levels_pattern})
        '''

            return filter_section
        
        except Exception as exception:
            self.__logger.error("Error generating filter configuration: {}".format(exception))
    

    def __rewrite_configurations(self, filter_section, output_section, file_path):
        try:

            with open(file_path, SystemDefinitions.FILE_READ_MODE) as file:
                existing_configuration = file.read()

            # Define the regex pattern to find the existing [FILTER] and [OUTPUT] sections
            filter_section_pattern = re.compile(r'\[FILTER\][\s\S]*?(?=\n\[|\n*$)', re.MULTILINE)
            output_section_pattern = re.compile(r'\[OUTPUT\][\s\S]*?(?=\n\[|\n*$)', re.MULTILINE)

            # Replace the existing [FILTER] and [OUTPUT] sections with the new ones
            updated_configuration = re.sub(filter_section_pattern, filter_section.strip(), existing_configuration)
            updated_config_content = re.sub(output_section_pattern, output_section.strip(), updated_configuration)

            with open(file_path, SystemDefinitions.FILE_WRITE_MODE) as file:
                file.write(updated_config_content)

            self.__logger.info("Successfully updated fluent-bit.conf with new configurations")
            return True
        
        except Exception as exception:
            self.__logger.error("Error updating fluent-bit.conf with new configurations: {}".format(exception))
            return False


    def __change_source_file_path_in_tasks(self, file_path):
        try:
            with open(self.__task_file_path, SystemDefinitions.FILE_READ_MODE) as file:
                playbook = yaml.safe_load(file)

            for task in playbook:
                if task.get("name") == "Copy the fluent-bit configuration":
                    if "copy" in task and "src" in task["copy"]:
                        task["copy"]["src"] = file_path

            with open(self.__task_file_path, SystemDefinitions.FILE_WRITE_MODE) as file:
                yaml.safe_dump(playbook, file, default_flow_style=False)

            self.__logger.info("Successfully updated the source path to {}".format(file_path))
            return True

        except Exception as exception:
            self.__logger.error("Error updating the source path: {}".format(exception))
            return False
        

    def __run_playbook_and_update_status(self):
        playbook_run_status, ansible_stats = HelperFunctions.run_playbook(playbook_path=self.__playbook_path)
        if playbook_run_status == True:
            
            if self._status_manager.update_status(message_dictionary = self._message_dictionary, ansible_stats = ansible_stats) == True:
                self.__logger.info("Successfully updated status in the ansible queue")
                return True
            else:
                self.__logger.error("Failed to update status in the ansible queue")
                return False
        else:
            return False