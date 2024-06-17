import yaml

import CoreCode.logger as Logger
import CoreCode.helper_functions as HelperFunctions
import Definitions.system_definitions as SystemDefinitions


ANSIBLE_HOST = "localhost"
ANSIBLE_USER = "chiefnet"

class InventoryManager():
    def __init__(self):
        self.__logger = Logger.get_logger(logger_name=__name__)

        self.__logger.info("InventoryManager initialization starts")   

        self.__inventory_file_path = SystemDefinitions.INVENTORY_FILE_PATH

        self.__logger.info("InventoryManager initialization ends")        


    def generate_inventory(self, content):
        try:
            status, id_and_port = HelperFunctions.get_ansible_queue_id_and_port_from_content(content, logger_object=self.__logger)
            if status:
                inventory = {
                    "all": {
                        "hosts": {}
                    }
                }

                for id, port in id_and_port.items():
                    host_name = id
                    inventory["all"]["hosts"][host_name] = {
                        "ansible_host": ANSIBLE_HOST,
                        "ansible_user": ANSIBLE_USER,
                        "ansible_port": port
                    }

                with open(self.__inventory_file_path, SystemDefinitions.FILE_WRITE_MODE) as inventory_file:
                    yaml.dump(inventory, inventory_file, default_flow_style=False)
                    
                return True
            else:
                self.__logger.error("Failed to get ansible queue id and port from content")
                return False

        except Exception as exception:
            self.__logger.error("An error occurred while generating inventory: {}".format(exception))
            return False
