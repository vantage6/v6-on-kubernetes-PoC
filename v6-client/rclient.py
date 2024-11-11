from vantage6.client import UserClient as Client

import config

# Initialize the client object, and run the authentication
client = Client(config.server_url, config.server_port, config.server_api, log_level='debug')
client.authenticate(config.username, config.password)

# Optional: setup the encryption, if you have an organization_key
client.setup_encryption(None)

input_ = {
    'method': 'partial',
    'kwargs': {"colname":"Age"}
}

average_task = client.task.create(
   collaboration=1,
   organizations=[4],
   name="poc_model",
   image="hcadavidescience/poc_model_training",
   description='',
   input_=input_,
   databases=[
      {'label': 'default'}
   ]
)