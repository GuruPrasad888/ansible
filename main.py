import signal
import sys

import Definitions.message_code_definitions as MessageCodeDefinitions

from CoreCode.configuration_manager import ConfigurationManager
from CoreCode.redis_manager import RedisManager
from CoreCode.database_manager import DatabaseManager
from CoreCode.inventory_manager import InventoryManager
from CoreCode.action_handler import ActionHandler
from CoreCode.status_manager import StatusManager

from CoreCode.authorized_keys_manager import AuthorizedKeysManager
from CoreCode.fluent_bit_manager import FluentbitManager


def sigterm_handler(_signo, _stack_frame):
    print("SIGTERM/SIGINT received. Exiting system")
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, sigterm_handler)
    signal.signal(signal.SIGTERM, sigterm_handler)

    configuration_manager = ConfigurationManager()
    redis_manager = RedisManager(configuration_manager=configuration_manager)
    database_manager = DatabaseManager(configuration_manager=configuration_manager)
    inventory_manager = InventoryManager()
    action_handler = ActionHandler(database_manager=database_manager, inventory_manager=inventory_manager)
    status_manager = StatusManager(database_manager=database_manager)

    redis_manager.register_receive_data_callback(receive_data_callback=action_handler.message_receive_callback)

    authorized_keys_manager = AuthorizedKeysManager(configuration_manager=configuration_manager ,database_manager=database_manager,status_manager=status_manager)
    fluent_bit_manager = FluentbitManager(database_manager=database_manager, status_manager=status_manager)

    action_handler.register_service_manager_callback(service_code=MessageCodeDefinitions.AUTHORIZED_KEYS_MANAGER, service_manager=authorized_keys_manager)
    action_handler.register_service_manager_callback(service_code=MessageCodeDefinitions.FLUENT_BIT_MANAGER, service_manager=fluent_bit_manager)
    
    
    signal.pause()