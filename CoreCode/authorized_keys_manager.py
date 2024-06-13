import os

import CoreCode.logger as Logger

from CoreCode.service_manager import ServiceManager

import Definitions.message_definitions as MessageDefinitions
import Definitions.system_definitions as SystemDefinitions
import Definitions.message_code_definitions as MessageCodeDefinitions

AUTHORIZED_KEYS_FILE_PATH = ".ssh/authorized_keys"
PATH_SEPERATOR_CHARACTER = os.path.sep


class AuthorizedKeysManager(ServiceManager):
    '''
    This module frames the status message itself and updates it via databae manager without status manager
    '''

    def __init__(self, configuration_manager, database_manager, status_manager):

        self.__logger = Logger.get_logger(logger_name=__name__)

        self.__logger.info("Authorized keys manager initializer starts")

        self._configuration_manager = configuration_manager
        self._database_manager = database_manager
        self._status_manager = status_manager

        self.__authorized_keys_file_path = self._configuration_manager.get_base_directory() + AUTHORIZED_KEYS_FILE_PATH
        
        event_dictionary = {}
        event_dictionary[MessageCodeDefinitions.UPDATE_AUTHORIZED_KEYS_EVENT] = self.__update_authorized_keys

        ServiceManager.__init__(self, status_manager= status_manager, event_dictionary=event_dictionary)

        self.__logger.info("Authorized keys manager initializer ends")

        
    def __update_authorized_keys(self):

        self.__logger.info("Update authorized keys event routine start")
        content = self._message_dictionary[MessageDefinitions.CONTENT_KEY]
        ansible_queue_id = next(iter(content.keys()))
        device_id = content[ansible_queue_id][0]

        status, ssh_keys = self._database_manager.get_ssh_key_and_update_status(device_id)
        
        if status == True:
            self.__logger.error(ssh_keys)
            try:
                if os.path.exists(self.__authorized_keys_file_path):
                    with open(self.__authorized_keys_file_path, SystemDefinitions.FILE_APPEND_MODE) as file:
                        for ssh_key in ssh_keys:
                            file.write(ssh_key)
                else:
                    ssh_dir = os.path.dirname(self.__authorized_keys_file_path)
                    os.makedirs(ssh_dir, exist_ok=True)
                    with open(self.__authorized_keys_file_path, SystemDefinitions.FILE_WRITE_MODE) as file:
                        for ssh_key in ssh_keys:
                            file.write(ssh_key)
                
                if self._status_manager.update_status(message_dictionary = self._message_dictionary, status = True) == True:
                    self.__logger.info("Update authorized keys event successful")
                    return True
                else:
                    self.__logger.error("Update authorized keys event failed")
                    return False

            except Exception as exception:
                self.__logger.error("Failed to update authorized_keys file with ssh_key: {}".format(exception))
                self._status_manager.update_status(message_dictionary = self._message_dictionary, status = False)
                return False
        else:
            self.__logger.error("Failed to get ssh key from database and update status in database")
            self._status_manager.update_status(message_dictionary = self._message_dictionary, status = False)
            return False
