import ansible_runner
import json

INVENTORY_PATH = "CoreCode/inventory.yml"


def run_playbook(playbook_path, logger_object):
    ansible_stats = {}

    try:
        runner = ansible_runner.run(
        playbook=playbook_path,
        inventory=INVENTORY_PATH,
        )

        ansible_stats = json.dumps(runner.stats)
        logger_object.info("Ansible playbook execution successful")
    
    except Exception as exception:
        logger_object.error("Error running ansible playbook: {}".format(exception))
        return ansible_stats


def get_ansible_queue_id_and_port_from_content(content, logger_object):
    id_and_port_dict = {}

    for id, value in content.items():
        if len(value) == 2:
            port = value[1]
            id_and_port_dict[id] = port
        else:
            logger_object.error()
            return False, id_and_port_dict
    
    logger_object.info()
    return True, id_and_port_dict


def get_device_id_and_port_from_content(content, logger_object):
    device_id_port_dict = {}

    for id, value in content.items():
        if len(value) == 2:
            device_id = value[0]
            port = value[1]
            device_id_port_dict[device_id] = port
        else:
            logger_object.error("Failed to get the device id and port from message dictionary")
            return False, device_id_port_dict
    
    logger_object.info("Successfully retrived device id and port from message dictionary")

    return True, device_id_port_dict


def get_device_id_from_content(content, logger_object):
    device_ids = []

    for id, value in content.items():
        if len(value) == 2:
            device_id = value[0]
            device_ids.append(device_id)
        else:
            logger_object.error()
            return False, device_ids
    
    logger_object.info()
    return True, device_ids


def get_ports_from_content(content, logger_object):
    ports = []

    for id, value in content.items():
        if len(value) == 2:
            port = value[1]
            ports.append(port)
        else:
            logger_object.error()
            return False, ports
    
    logger_object.info()
    return True, ports