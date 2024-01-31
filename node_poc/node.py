from container_manager import ContainerManager
import time
import socketio
import os
import json

container_manager = ContainerManager()


def run_algorithm(json_input):
    #container_manager.create_volume(json_input["tmp_vol_name"])
    container_manager.run(run_id=json_input["run_id"],
               image=json_input["image"],
               tmp_vol_name=json_input["tmp_vol_name"],
               task_info=json_input["task_info"],
               docker_input=None,databases_to_use=None,token=None)



# Get the host IP from the environment variable
host_ip = os.environ['HOST_IP']

print(f"Starting node at {host_ip}")

sio = socketio.Client()


@sio.event
def connect():
    print("Connected to server")    
    sio.emit('node_connection_request', '')

@sio.event
def disconnect():
    print("Disconnected from server")

@sio.event
def reply(data):
    print("Received reply: ", data)

@sio.event
def command(data):
    print("Executing command: ", data)
    run_algorithm(data)



if __name__ == '__main__':
    sio.connect(f'http://{host_ip}:5000')
    sio.wait()







