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



res = run_algorithm(
    {
    "run_id": 200000013,
    "task_info": {"arg1":"/app/input/csv/default","arg2":"Age","arg3":"/app/output/avg.txt"},
    "image": "hectorcadavid/v6_average_algorithm",
    "docker_input": "input1",
    "tmp_vol_name": "example-tmp-vol",
    "token": "example_token",
    "databases_to_use": ["default","db1", "db2", "db3"]
    }
)


res = run_algorithm(
    {
    "run_id": 200000014,
    "task_info": {"arg1":"/app/input/csv/defaultxxx","arg2":"Age","arg3":"/app/output/avg.txt"},
    "image": "hectorcadavid/v6_average_algorithm",
    "docker_input": "input1",
    "tmp_vol_name": "example-tmp-vol",
    "token": "example_token",
    "databases_to_use": ["default","db1", "db2", "db3"]
    }
)



print("Polling changes")    
while True:    
    time.sleep(10)
    r = container_manager.get_result()
    if r!=None:
        print(r)

print(type(res))
print(f'Execution result:{res}')

#print(container_manager.is_running("100000009"))