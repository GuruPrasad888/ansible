import CoreCode.logger as Logger


import Definitions.message_definitions as MessageDefinitions
import Definitions.system_definitions as SystemDefinitions
import Definitions.message_code_definitions as MessageCodeDefinitions

import CoreCode.helper_functions as HelperFunctions


class ServiceManager():
    logger = Logger.get_logger(__name__)

    def __init__(self, status_manager, event_dictionary):

        ServiceManager.logger.info("ServiceManager initializer starts")

        self._status_manager = status_manager

        self.__event_dictionary = event_dictionary

        ServiceManager.logger.info("ServiceManager initializer ends")


    def service_handler_function(self, message_dictionary):
        """
        This function must be registered with action handler to receive data from the user
        Args    - message_dictionary : dict type - the JSON message sent by the Websocket server parsed into a dictionary
        Returns - None
        Raises  - None
        """
        self._message_dictionary = message_dictionary        

        try:
            event_code = self._message_dictionary[MessageDefinitions.EVENT_CODE_KEY]
            service_code = self._message_dictionary[MessageDefinitions.SERVICE_CODE_KEY]
        except KeyError as key_error:
            ServiceManager.logger.error(key_error)
        except Exception as exception:
            ServiceManager.logger.error(exception)

        event_routine = self.__fetch_event_routine(event_code=event_code)

        ServiceManager.logger.info("Service {} Event {} starts".format(service_code, event_code))

        if event_routine() == True: 
            ServiceManager.logger.info("Service {} Event {} successful".format(service_code, event_code))
        else:
            ServiceManager.logger.error("Service {} Event {} failed/unavailable".format(service_code, event_code))

        ServiceManager.logger.info("Service {} Event {} ends".format(service_code, event_code))


    def __fetch_event_routine(self, event_code):        
        if event_code not in self.__event_dictionary:
            self._status_manager.update_status(message_dictionary = self._message_dictionary, status = False)
            
        return self.__event_dictionary.get(event_code, lambda : False)
    