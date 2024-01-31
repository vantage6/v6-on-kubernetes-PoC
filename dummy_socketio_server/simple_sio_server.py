import socketio
import eventlet
import threading

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
    app = socketio.WSGIApp(sio)
    eventlet.wsgi.server(eventlet.listen(('192.168.178.185',5000)), app)
    print('Socket.io server running')