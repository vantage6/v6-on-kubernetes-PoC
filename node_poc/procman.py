from container_manager import ContainerManager
import time
import socketio
import os
import json

container_manager = ContainerManager()

print(container_manager.is_running("200000009"))