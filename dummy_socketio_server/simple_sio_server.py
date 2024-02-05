import socketio
import eventlet
import threading
import yaml

# create a Socket.IO server
sio = socketio.Server()

node_client_sid = -1

@sio.event
def connect(sid, environ):
    print("Client connected: ", sid)       

@sio.event
def disconnect(sid):
    print("Client disconnected: ", sid)


@sio.event
def node_connection_request(sid, data):
    global node_client_sid
    print("Connection request from ", sid, " with data ", data)
    node_client_sid = sid

@sio.event
def command_request(sid, data):
    global node_client_sid
    print("Command request from ", sid, " - Sending command to ", node_client_sid)
    sio.emit('command', data, room=node_client_sid)    


if __name__ == '__main__':

    with open('server_config.yaml', 'r') as file:
        v6_config = yaml.safe_load(file)
        print(f'v6 dummy server settings:{v6_config}')


    app = socketio.WSGIApp(sio)
    eventlet.wsgi.server(eventlet.listen((v6_config['server_ip'],v6_config['port'])), app)
    print('Socket.io server running')