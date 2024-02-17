import socketio
import time

sio = socketio.Client()
sio.connect('http://192.168.178.185:5000')


run_cmd_payload = {
    "run_id": 33333312,
    "task_info": {"arg1":"/app/input/csv/default","arg2":"Age","arg3":"/app/output/avg.txt"},
    "image": "clgeng/v6_average_algorithm",
    "docker_input": "input1",
    "tmp_vol_name": "example-tmp-vol",
    "token": "example_token",
    "databases_to_use": ["default","db1", "db2", "db3"]
    }

sio.emit('command_request',run_cmd_payload)
time.sleep(3)
sio.disconnect()
