import json
import queue
import threading

import CoreCode.logger as Logger

import Definitions.message_definitions as MessageDefinitions
import Definitions.message_code_definitions as MessageCodeDefinitions


class ActionHandler():

    def __init__(self, database_manager, inventory_manager):
        self.__logger = Logger.get_logger(logger_name=__name__)

        self.__logger.info("ActionHandler object initialization starts")
        
        self._database_manager = database_manager
        self._inventory_manager = inventory_manager

        self.__service_manager_dictionary = {}                               

        self.__received_message_queue = queue.Queue()
        
        self.__message_received_event = threading.Event()
        self.__message_received_event.clear()

        self.__message_handler_thread = threading.Thread(target=self.__message_handler_thread_function, daemon=True)
        self.__message_handler_thread.start()

        self.__logger.info("ActionHandler object initialization ends")


    def register_service_manager_callback(self, service_code, service_manager):
        """
        This function is used to register the service manager callbacks with the action handler.
        Each service manager has a unique service code which must be provided while registering the callback
        Args   - service_code - integer type service code corresponding to the service manager being registered
                 service_manager - an instance of type ServiceManager must be registered
        Return - None
        Raises - None
        """
        self.__service_manager_dictionary[service_code] = service_manager


    def message_receive_callback(self, message):
        """
        This callback is registered with the communication module. A message received from the user
        through the communication module is passed as an argument to this callback function
        Args   - message - placeholder to receive message from the user
        Return - None
        Raises - None
        """
        self.__received_message_queue.put(message)
        self.__message_received_event.set()

    
    def __message_handler_thread_function(self):
        while self.__message_received_event.wait():
            message = self.__received_message_queue.get()
            if message.strip():
                status = {}
                data = self._database_manager.get_data_from_ansible_queue(message=message)  
                data_validation_status, validated_data =  self.__validate_and_parse_data(data=data)

                if data_validation_status == True:
                    if validated_data[MessageDefinitions.SERVICE_CODE_KEY] != MessageCodeDefinitions.AUTHORIZED_KEYS_MANAGER:    #Updating authorized keys doesn't require inventory
                        if self._inventory_manager.generate_inventory(validated_data[MessageDefinitions.CONTENT_KEY]) == True:
                            pass
                        else:
                            self.__logger.error("Failed to generate inventory")
                            self._status_manager.update_status(message_dictionary = self._message_dictionary, status = False)
                            continue

                    self.__service_manager_dictionary[validated_data[MessageDefinitions.SERVICE_CODE_KEY]].service_handler_function(validated_data)
                else:
                    self.__logger.error("Data validation failed")
            else:
                self.__logger.error("Empty message received in redis channel")


    def __validate_and_parse_data(self, data):

        validation_status = False
        parsed_data = {}

        try:
            organization_id = data.get(MessageDefinitions.ORGANIZATION_ID_KEY)
            service_code = data.get(MessageDefinitions.SERVICE_CODE_KEY)
            event_code = data.get(MessageDefinitions.EVENT_CODE_KEY)
            device_id_port_dict = data.get(MessageDefinitions.CONTENT_KEY)

            first_service_code = service_code[0]
            first_event_code = event_code[0]
            first_organization_id = organization_id[0]

            if first_service_code not in self.__service_manager_dictionary:
                self.__logger.error("User specified service code not registered with action_handler")
                return validation_status, parsed_data

            if not all(element == first_service_code for element in service_code):
                self.__logger.error("Multiple tasks received in same message")
                return validation_status, parsed_data
            
            if not all(element == first_event_code for element in event_code):
                self.__logger.error("Multiple events received in same message")
                return validation_status, parsed_data
            
            if not all(element == first_organization_id for element in organization_id):
                self.__logger.error("Multiple organization ids received in same message")
                return validation_status, parsed_data
            
            validation_status = True

            parsed_data[MessageDefinitions.ORGANIZATION_ID_KEY] = first_organization_id
            parsed_data[MessageDefinitions.SERVICE_CODE_KEY] = first_service_code
            parsed_data[MessageDefinitions.EVENT_CODE_KEY] = first_event_code
            parsed_data[MessageDefinitions.CONTENT_KEY] = device_id_port_dict

            self.__logger.info("Data validation success")

        except Exception as exception:
            self.__logger.error("Error in validating data {}".format(exception))
            return validation_status, parsed_data
        
        return validation_status, parsed_data
