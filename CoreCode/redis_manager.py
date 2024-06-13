import redis
import asyncio
import threading

import CoreCode.logger as Logger

import Definitions.system_definitions as SystemDefinitions

REDIS_HOST = "redis_host"
REDIS_PORT = "redis_port"
REDIS_CHANNEL = "redis_channel"
REDIS_PASSWORD = "redis_password"

class RedisManager():
    
    def __init__(self, configuration_manager):

        self.__logger = Logger.get_logger(__name__)
        self.__logger.info("RedisManager initialization starts")

        self._configuration_manager = configuration_manager

        self.__redis_event_loop = asyncio.new_event_loop()
        self.__redis_event_thread = threading.Thread(target=self.__redis_thread_function, daemon=True)
        self.__redis_event_thread.start()
        self.__logger.info("RedisManager initialization ends")


    def register_receive_data_callback(self, receive_data_callback):
        """
        Registers a callback function to handle data received from the Redis channel.

        Args:
            receive_data_callback: Callable function that takes a string as an argument.
        """
        self.__receive_data_callback = receive_data_callback


    def __redis_thread_function(self):
        # set a new event loop as the default loop for this thread
        asyncio.set_event_loop(self.__redis_event_loop)

        self.__redis_event_loop.create_task(self.__connection_handler_async())
        self.__redis_event_loop.run_forever()


    async def __connection_handler_async(self):
        redis_configuration = self._configuration_manager.get_redis_configuration()
        while True:  # Loop to ensure persistent connection and reconnection handling
            try:
                connection = redis.Redis(host=redis_configuration[REDIS_HOST],
                                         port=redis_configuration[REDIS_PORT], 
                                         password=redis_configuration[REDIS_PASSWORD])
                
                pubsub = connection.pubsub()
                pubsub.subscribe(redis_configuration[REDIS_CHANNEL])
                self.__logger.info("Subscribed to Redis channel {}".format(redis_configuration[REDIS_CHANNEL]))

                await self.__receive_data_async(pubsub)

                self.__logger.info("Disconnected from Redis channel {}".format(redis_configuration[REDIS_CHANNEL]))

            except Exception as exception:
                self.__logger.error("Connection handler error: {}".format(exception))
                await asyncio.sleep(1)  # Delay before attempting to reconnect


    async def __receive_data_async(self, pubsub):
        try:
            for message in pubsub.listen():  # Blocking call, will run indefinitely
                if message["type"] == "message":
                    data = message["data"].decode("utf-8")
                    self.__receive_data_callback(data)
        except Exception as exception:
            self.__logger.exception(f"Receive data error: {exception}")
            pass