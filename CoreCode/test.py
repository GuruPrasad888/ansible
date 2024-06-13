import psutil

def get_process_by_port(port):
    """
    Get the process running on the specified port.

    :param port: Port number to search for.
    :return: psutil.Process object or None if no process is found.
    """
    for conn in psutil.net_connections(kind='inet'):
        if conn.laddr.port == port:
            return psutil.Process(conn.pid)
    return None

def kill_process_by_port(port):
    """
    Kill the process running on the specified port.

    :param port: Port number to search for.
    :return: True if process is killed, False otherwise.
    """
    process = get_process_by_port(port)
    if process:
        try:
            process.terminate()  # or process.kill() for a more forceful termination
            process.wait(timeout=5)  # wait for the process to terminate
            print(f"Process on port {port} has been terminated.")
            return True
        except psutil.NoSuchProcess:
            print(f"No process found on port {port}.")
        except psutil.AccessDenied:
            print(f"Access denied when trying to terminate the process on port {port}.")
        except psutil.TimeoutExpired:
            print(f"Timeout expired while waiting for the process on port {port} to terminate.")
    else:
        print(f"No process found on port {port}.")
    return False

if __name__ == "__main__":
    port_to_kill = 5001  # Replace with your specific port number
    kill_process_by_port(port_to_kill)