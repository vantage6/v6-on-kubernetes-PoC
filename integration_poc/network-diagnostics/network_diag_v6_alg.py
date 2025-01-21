from vantage6.client import UserClient as Client

# Note: we assume here the config.py you just created is in the current directory.
# If it is not, then you need to make sure it can be found on your PYTHONPATH
import config

# Initialize the client object, and run the authentication
client = Client(config.server_url, config.server_port, config.server_api,
                log_level='debug')
client.authenticate(config.username, config.password)

# Optional: setup the encryption, if you have an organization_key
client.setup_encryption(None)

input_ = {
    'method': 'central',
    'kwargs': {"sleep_time":"1"}
}

network_diag_task = client.task.create(
   collaboration=1,
   organizations=[4],
   name="nwdiag",   
   image="ghcr.io/hcadavid/k8s-policies-network-diagnostics:latest",
   #Built from https://github.com/hcadavid/k8s-policies-network-diagnostics
   description='',
   input_=input_,
   databases=[
      #{'label': 'default'}
   ]
)

task_id = network_diag_task['id']
print('Waiting for results...')
result = client.wait_for_results(task_id)
print('Results received!')
print(result)