from datetime import datetime
import pytz
import json

import CoreCode.logger as Logger

from sqlalchemy import create_engine, update, Column, Integer, Text, BigInteger, String, DateTime, Boolean, JSON
from sqlalchemy.orm import sessionmaker, declarative_base

import Definitions.message_definitions as MessageDefinitions

import CoreCode.helper_functions as HelperFunctions

DB_USER = "db_user"
DB_PASSWORD = "db_password"
DB_HOST = "db_host"
DB_PORT = "db_port"
DB_NAME = "db_name"

TIMEZONE = "Asia/Kolkata"
IN_PROGRESS_KEYWORD = "in_progress"

COMPLETED = "completed"
FAILED = "failed"


Base = declarative_base()   # Define the base class for declarative models

# Define your model classes
class DeviceKeys(Base):
    __tablename__ = "device_ssh_keys"

    id = Column(BigInteger, primary_key=True)
    device_id = Column(BigInteger)
    ssh_key = Column(Text)
    is_ssh_key_synced = Column(Boolean)
    ssh_key_synced_at = Column(DateTime)
    ssh_port = Column(Integer)
    is_ssh_tunnel_enabled = Column(Boolean)
    deleted_at = Column(DateTime)


class AnsibleQueue(Base):
    __tablename__ = "ansible_queues"

    id = Column(BigInteger, primary_key=True)
    device_id = Column(BigInteger)
    organization_id = Column(BigInteger)
    service_code = Column(Integer)
    event_code = Column(Integer)
    ssh_port = Column(Integer)
    state = Column(String)
    state_updated_at = Column(DateTime)

    
class LogForwarding(Base):
    __tablename__ = "log_forwarding"

    id = Column(BigInteger, primary_key=True)
    organization_id = Column(BigInteger)
    is_external_forwarding_enabled = Column(Boolean)
    log_destination = Column(String)
    log_value = Column(JSON)


class DatabaseManager:
    def __init__(self, configuration_manager):
        self.__logger = Logger.get_logger(logger_name=__name__)
        self.__logger.info("DatabaseManager initialization starts")      

        self._configuration_manager = configuration_manager  
        postgres_configuration = self._configuration_manager.get_postgres_configuration()

        database_url = "postgresql://{0}:{1}@{2}:{3}/{4}".format(postgres_configuration[DB_USER],
                                                                 postgres_configuration[DB_PASSWORD],
                                                                 postgres_configuration[DB_HOST],
                                                                 postgres_configuration[DB_PORT],
                                                                 postgres_configuration[DB_NAME])
        self.engine = create_engine(database_url) 
        self.Session = sessionmaker(bind=self.engine)
        self.__session = self.Session()
        self.__logger.info("DatabaseManager initialization ends")        


#AnsibleQueue
    def get_data_from_ansible_queue(self, message):
        ids = [int(item) for item in json.loads(message)]

        data = {}
        service_codes = []
        event_codes = []
        organization_ids = []
        content = {}

        try:
            query_result = self.__session.query(
                AnsibleQueue.id,
                AnsibleQueue.device_id,
                AnsibleQueue.ssh_port,
                AnsibleQueue.service_code,
                AnsibleQueue.event_code,
                AnsibleQueue.organization_id
            ).filter(AnsibleQueue.id.in_(ids)).all()

            for record in query_result:
                device_id = record.device_id
                ssh_port = record.ssh_port
                service_code = record.service_code
                event_code = record.event_code
                organization_id = record.organization_id

                service_codes.append(service_code)
                event_codes.append(event_code)
                organization_ids.append(organization_id)

                # Create a nested dictionary with id as key and [device_id, ssh_port] as value
                if ssh_port is not None:    # ssh_port is None for update authorized keys
                    content[int(record.id)] = [int(device_id), int(ssh_port)]
                else:
                    content[int(record.id)] = [int(device_id), ssh_port]

            data[MessageDefinitions.ORGANIZATION_ID_KEY] = organization_ids
            data[MessageDefinitions.SERVICE_CODE_KEY] = service_codes
            data[MessageDefinitions.EVENT_CODE_KEY] = event_codes
            data[MessageDefinitions.CONTENT_KEY] = content
            self.__logger.info("Successfuly queried for data from the AnsibleQueue")
        
        except Exception as exception:
            self.__logger.error("An error occurred while getting data from AnsibleQueue: {}".format(exception))
            return data

        return data


    def update_status_in_ansible_queue(self, data):
        current_time = datetime.now(pytz.timezone(TIMEZONE))
        current_time_str = current_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3] + current_time.strftime('%z')
        try:
            if data[MessageDefinitions.SUCCESS_KEYWORD]:

                self.__session.query(AnsibleQueue).filter(
                    AnsibleQueue.id.in_(data[MessageDefinitions.SUCCESS_KEYWORD])
                ).update(
                    {
                        AnsibleQueue.state: COMPLETED,
                        AnsibleQueue.state_updated_at: current_time_str
                    },
                    synchronize_session=False
                )

            if data[MessageDefinitions.FAILED_KEYWORD]:
                self.__session.query(AnsibleQueue).filter(
                    AnsibleQueue.id.in_(data[MessageDefinitions.FAILED_KEYWORD])
                ).update(
                    {
                        AnsibleQueue.state: FAILED,
                        AnsibleQueue.state_updated_at: current_time_str
                    },
                    synchronize_session=False
                        )

            self.__session.commit()
            self.__logger.info("Successfully updated status in the ansible queue")
            return True
        
        except Exception as exception:
            self.__session.rollback()
            self.__logger.error("Failed to update status in ansible queue: {}".format(exception))
            return False
        

    def get_ports_to_kill(self, message_dictionary):

        ports_to_be_killed = {}

        try:
            status, current_ports = HelperFunctions.get_device_id_and_port_from_content(message_dictionary[MessageDefinitions.CONTENT_KEY], logger_object=self.__logger)
            if status == True:
                if not all(port is None for port in current_ports.values()):    # Check if all ports are None

                    inprogress_ports = self.__session.query(AnsibleQueue.ssh_port).filter(
                        AnsibleQueue.state == IN_PROGRESS_KEYWORD
                    ).all()

                    inprogress_ports = [port for port in inprogress_ports]
                    for device_id, port in current_ports.items():
                        if port not in inprogress_ports:
                            ports_to_be_killed[device_id] = port
                    self.__logger.info("Successfully got the ports to be killed")
                else:
                    self.__logger.info("All ports are none in the message dictionary")
            else:
                self.__logger.error("Failed to get ports from the message dictionary")
                return ports_to_be_killed

        except Exception as exception:
            self.__logger.error("Failed to get the list of ports to be killed: {}".format(exception))
            return ports_to_be_killed
        
        return ports_to_be_killed


#DeviceKeys
    def get_ssh_key_and_update_status(self, device_id):
        ssh_keys = []
        try:
            ssh_keys_query = self.__session.query(DeviceKeys.ssh_key).filter(DeviceKeys.deleted_at == None).all()
            
            ssh_keys = [record.ssh_key for record in ssh_keys_query]

            current_time = datetime.now(pytz.timezone(TIMEZONE))
            current_time_str = current_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3] + current_time.strftime('%z')

            self.__session.execute(
                update(DeviceKeys)
                .where(DeviceKeys.device_id == device_id)
                .values(is_ssh_key_synced=True, ssh_key_synced_at=current_time_str)
            )
            self.__session.commit()
            self.__logger.info("Successfully queried ssh key and updated status")
            
        except Exception as exception:
            self.__session.rollback()
            self.__logger.error("Failed to get ssh key and update status: {}".format(exception))
            return ssh_keys
        
        return ssh_keys
    

    def update_port_status_in_device_keys(self, device_ids):
        try:
            self.__session.query(DeviceKeys).filter(DeviceKeys.device_id.in_(device_ids)).update(
                {
                    DeviceKeys.ssh_port: None,
                    DeviceKeys.is_ssh_tunnel_enabled: False
                },
                synchronize_session=False
            )
            self.__session.commit()
            self.__logger.info("Successfully updated port status in device keys table")
            return True
        
        except Exception as exception:
            self.__session.rollback()
            print("Updating port status in device keys table failed: {}".format(exception))
            return False
 

#LogForwarding
    def get_fluentbit_configuration(self, organization_id):
        result = {}
        try:

            org_entry = self.__session.query(LogForwarding).filter(LogForwarding.organization_id == organization_id).first()

            if org_entry:
                if org_entry.is_external_forwarding_enabled:
                    result = {
                        "log_type": org_entry.log_destination,
                        "log_value": org_entry.log_value
                    }
                else:
                    null_org_entry = self.__session.query(LogForwarding).filter(LogForwarding.organization_id == None).first()
                    if null_org_entry:
                        result = {
                            "log_type": null_org_entry.log_destination,
                            "log_value": null_org_entry.log_value
                        }
            else:
                null_org_entry = self.__session.query(LogForwarding).filter(LogForwarding.organization_id == None).first()
                if null_org_entry:
                    result = {
                        "log_type": null_org_entry.log_destination,
                        "log_value": null_org_entry.log_value
                    }

            self.__logger.info("Successfully queried log forwarding details")
            return result
        
        except Exception as exception:
            self.__logger.error("Failed to get the log forwarding details{}".format(exception))