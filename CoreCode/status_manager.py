import psutil

import CoreCode.logger as Logger

import Definitions.message_definitions as MessageDefinitions

PROCESSED_KEYWORD = "processed"
DARK_KEYWORD = "dark"
FAILURES_KEYWORD = "failures"
IGNORED_KEYWORD = "ignored"
RESCUED_KEYWORD = "rescued"


class StatusManager():
    def __init__(self, database_manager):
        self.__logger = Logger.get_logger(__name__)
        self.__logger.info("StatusManager initialization starts")

        self._database_manager = database_manager

        self.__logger.info("StatusManager initialization ends")


    def update_status(self, message_dictionary=None, ansible_stats=None, status=None):

        if ansible_stats is not None:
            try:
                parsed_stats = self.__parse_ansible_runner_stats(ansible_stats)
                if self.__update_status_in_database(message_dictionary=message_dictionary, status=parsed_stats):
                    return True
                else:
                    return False
            except Exception as exception:
                self.__logger.error("Updating status failed {}".format(exception))
                return False

        elif status is not None:
            try:
                framed_status = {MessageDefinitions.SUCCESS_KEYWORD: [], MessageDefinitions.FAILED_KEYWORD: []}

                if status == True:
                    framed_status[MessageDefinitions.SUCCESS_KEYWORD] = list(message_dictionary[MessageDefinitions.CONTENT_KEY].keys())
                else:
                    framed_status[MessageDefinitions.FAILED_KEYWORD] = list(message_dictionary[MessageDefinitions.CONTENT_KEY].keys())

                if self.__update_status_in_database(message_dictionary=message_dictionary, status=framed_status):
                    return True
                else:
                    return False
            except Exception as exception:
                self.__logger.error("Updating status failed {}".format(exception))


    def __parse_ansible_runner_stats(self, stats):
        parsed_stats = {MessageDefinitions.SUCCESS_KEYWORD: [],MessageDefinitions.FAILED_KEYWORD: []}

        processed_devices = stats.get(PROCESSED_KEYWORD, {}).keys()
    
        for id in processed_devices:
            # Check failure conditions
            if (id in stats.get(DARK_KEYWORD, {}) or
                id in stats.get(FAILURES_KEYWORD, {}) or
                id in stats.get(IGNORED_KEYWORD, {}) or
                id in stats.get(RESCUED_KEYWORD, {})):
                    parsed_stats[MessageDefinitions.FAILED_KEYWORD].append(int(id))
                    self.__logger.error("Ansible task failed for the device in ansible queue: {}".format(id))

            else:
                parsed_stats[MessageDefinitions.SUCCESS_KEYWORD].append(int(id))
                self.__logger.info("Ansible task successful for the device in the ansible queue: {}".format(id))


    def __update_status_in_database(self, message_dictionary, status):
        if self._database_manager.update_status_in_ansible_queue(status) == True:
            status, ports_to_kill = self._database_manager.get_ports_to_kill(message_dictionary)    # ports_to_kill is a dictionary {device_id:port}
            
            if status == True:
                if ports_to_kill != {}:
                    device_ids =  self.__kill_processes_on_ports(ports_to_kill=ports_to_kill)
                    if self._database_manager.update_port_status_in_device_keys(device_ids) == True:
                        return True
                    else:
                        return False
                else:
                    self.__logger.info("No ports founnd to kill processess")
                    return True
            else:
                self.__logger.error("Failed to get the ports to be killed. Hence failed to kill the processes")
                return False         
        else:
            self.__logger.error("Updating status in ansible queue failed. Hence failed to get the list of ports to kill")
            return False        
            

    def __kill_processes_on_ports(self, ports_to_kill):
        device_ids = []
        for device_id, port in ports_to_kill.items():
            process = self.__get_process_by_port(port)
            if process:
                try:
                    process.terminate()  # or process.kill() for a more forceful termination
                    process.wait(timeout=5)  # wait for the process to terminate
                    self.__logger.info("Process on port {} has been terminated".format(port))
                    device_ids.append(device_id)
                except psutil.NoSuchProcess:
                    self.__logger.error("No process found on port {}".format(port))
                except psutil.AccessDenied:
                    self.__logger.error("Access denied when trying to terminate the process on port {}".format(port))
                except psutil.TimeoutExpired:
                    self.__logger.error("Timeout expired while waiting for the process on port {} to terminate".format(port))


    def __get_process_by_port(self, port):
        try:

            for conn in psutil.net_connections(kind='inet'):
                if conn.laddr.port == port:
                    return psutil.Process(conn.pid)
            return None
        except Exception as exception:
            self.__logger.error("Failed to get the process for port {}".format(port))
            return None

         




'''stats_sample = {
    "skipped": {
        "1": 4
    },
    "ok": {
        "1": 3
    },
    "dark": {
        "2": 1
    },
    "failures": {},
    "ignored": {},
    "rescued": {},
    "processed": {
        "2": 1,
        "1": 1
    },
    "changed": {
        "1": 1
    }
}'''