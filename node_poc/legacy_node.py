from vantage6.common.client.node_client import NodeClient
from threading import Thread
from vantage6.node import proxy_server
from vantage6.common.log import get_file_logger
from gevent.pywsgi import WSGIServer
from vantage6.common.exceptions import AuthenticationException
from vantage6.common import logger_name
from vantage6.node.socket import NodeTaskNamespace
from vantage6.cli.context.node import NodeContext

from vantage6.node.globals import (
    NODE_PROXY_SERVER_HOSTNAME,
    SLEEP_BTWN_NODE_LOGIN_TRIES,
    TIME_LIMIT_RETRY_CONNECT_NODE,
    TIME_LIMIT_INITIAL_CONNECTION_WEBSOCKET,
)

from socketio import Client as SocketIO
import logging
from logging import handlers
import traceback
import random
import requests
import time
import os
import queue

# Based on https://github.com/vantage6/vantage6/blob/be2e82b33e68db74304ea01c778094e6b40e671a/vantage6-node/vantage6/node/__init__.py#L1

class NodePod:

    def __init__(self):
        self.log = logging.getLogger(logger_name(__name__))

        # Initialize the node. If it crashes, shut down the parts that started
        # already
        try:
            self.initialize()
        except Exception:
            self.cleanup()
            raise    

    
    def initialize(self, ctx: NodeContext) -> None:

        self.client = NodeClient(
                    host="https://v6-server.tail984a0.ts.net",
                    port="443",
                    path="/api",
                )
        self.log.info(f"Connecting server: {self.client.base_path}")
        self.queue = queue.Queue()
        self.log.debug("Authenticating")
        self.authenticate()

        #TODO check/setup collaboration encryption status
        self.setup_encryption()

        # Thread for proxy server for algorithm containers, so they can
        # communicate with the central server.
        t = Thread(target=self.__proxy_server_worker, daemon=True)
        t.start()

        # Create a long-lasting websocket connection.
        self.log.debug("Creating websocket connection with the server")
        self.connect_to_socket()

        #TODO listen and process incoming messages
        self.log.info("Init complete")
        print("Keep running the main thread until the proxy server is listening")
        t.join()

    def __print_connection_error_logs(self):
        """Print error message when node cannot find the server"""
        self.log.warning("Could not connect to the server. Retrying in 10 seconds")


    def setup_encryption(self) -> None:
        #TODO check collaboration encryption configuration    
        """Setup encryption if the node is part of encrypted collaboration"""
        """
        encrypted_collaboration = self.client.is_encrypted_collaboration()
        encrypted_node = self.config["encryption"]["enabled"]

        if encrypted_collaboration != encrypted_node:
            # You can't force it if it just ain't right, you know?
            raise Exception("Expectations on encryption don't match?!")

        if encrypted_collaboration:
            self.log.warn("Enabling encryption!")
            private_key_file = self.private_key_filename()
            self.client.setup_encryption(private_key_file)

        else:
            self.log.warn("Disabling encryption!")
            self.client.setup_encryption(None)
        """
        self.client.setup_encryption(None)


    def authenticate(self):
        """
        Authenticate with the server using the api-key from the configuration
        file. If the server rejects for any reason -other than a wrong API key-
        serveral attempts are taken to retry.
        """

        TIME_LIMIT_RETRY_CONNECT_NODE = 60
        SLEEP_BTWN_NODE_LOGIN_TRIES = 2

        api_key = "1b44626c-c7db-4712-bc29-467a73b79445"

        success = False
        i = 0
        while i < TIME_LIMIT_RETRY_CONNECT_NODE / SLEEP_BTWN_NODE_LOGIN_TRIES:
            i = i + 1
            try:
                self.client.authenticate(api_key)

            except AuthenticationException as e:
                msg = "Authentication failed: API key is wrong!"
                self.log.warning(msg)
                self.log.warning(e)
                break
            except requests.exceptions.ConnectionError:
                self.__print_connection_error_logs()
                time.sleep(SLEEP_BTWN_NODE_LOGIN_TRIES)
            except Exception as e:
                msg = (
                    "Authentication failed. Retrying in "
                    f"{SLEEP_BTWN_NODE_LOGIN_TRIES} seconds!"
                )
                self.log.warning(msg)
                self.log.warning(e)
                time.sleep(SLEEP_BTWN_NODE_LOGIN_TRIES)

            else:
                # This is only executed if try-block executed without error.
                success = True
                break

        if success:
            self.log.info(f"Node name: {self.client.name}")
        else:
            self.log.critical("Unable to authenticate. Exiting")
            exit(1)

        # start thread to keep the connection alive by refreshing the token
        self.client.auto_refresh_token()        


    def __proxy_server_worker(self) -> None:
        
        """
        Proxy algorithm container communcation.

        A proxy for communication between algorithms and central
        server.
        """
        #if self.ctx.running_in_docker:
            # NODE_PROXY_SERVER_HOSTNAME points to the name of the proxy
            # when running in the isolated docker network.
            #default_proxy_host = "127.0.0.1"
        #else:
            # If we're running non-dockerized, assume that the proxy is
            # accessible from within the docker algorithm container on
            # host.docker.internal.
            #default_proxy_host = "host.docker.internal"
        default_proxy_host = "localhost"

        # If PROXY_SERVER_HOST was set in the environment, it overrides our
        # value.
        
        proxy_host = os.environ.get("PROXY_SERVER_HOST", default_proxy_host)
        #os.environ["PROXY_SERVER_HOST"] = proxy_host

        #proxy_port = int(os.environ.get("PROXY_SERVER_PORT", 8080))
        proxy_port = 4567

        """
        try:

            # 'app' is defined in vantage6.node.proxy_server
            
            debug_mode = self.debug.get("proxy_server", False)
            if debug_mode:
                self.log.debug("Debug mode enabled for proxy server")
                proxy_server.app.debug = True
            proxy_server.app.config["SERVER_IO"] = self.client
            proxy_server.server_url = self.client.base_path

        except Exception as e:
            print(e)
        """
        try:

            # set up proxy server logging
            #log_level = getattr(logging, self.config["logging"]["level"].upper())
            #self.proxy_log = get_file_logger(
            #    #"proxy_server", self.ctx.proxy_log_file, log_level_file=log_level
            #    "proxy_server", './test_log_file.txt', log_level_file=logging.DEBUG, log_level_console = logging.DEBUG,
            #)
        
            # this is where we try to find a port for the proxyserver
            for try_number in range(5):
                self.log.info("Starting proxyserver at '%s:%s'", proxy_host, proxy_port)
                http_server = WSGIServer(
                    ("0.0.0.0", proxy_port), proxy_server.app #, log=self.proxy_log
                )                        
                try:
                    print('Starting proxy')
                    http_server.serve_forever()
                except OSError as e:
                    print(e)
                    self.log.info("Error during attempt %s", try_number)
                    self.log.info("%s: %s", type(e), e)
                    if e.errno == 48:
                        proxy_port = random.randint(2048, 16384)
                        self.log.warning("Retrying with a different port: %s", proxy_port)
                        os.environ["PROXY_SERVER_PORT"] = str(proxy_port)

                    else:
                        raise

                except Exception as e:
                    print(e)
                    self.log.error("Proxyserver could not be started or crashed!")
                    self.log.error(e)
        except Exception as e:
            print("Exception catched")
            print(e)
            

    def connect_to_socket(self) -> None:
        """
        Create long-lasting websocket connection with the server. The
        connection is used to receive status updates, such as new tasks.
        """
        #debug_mode = self.debug.get("socketio", False)
        #if debug_mode:
        #    self.log.debug("Debug mode enabled for socketio")
        
        self.socketIO = SocketIO(
            request_timeout=60 #, logger=debug_mode, engineio_logger=debug_mode
        )

        self.socketIO.register_namespace(NodeTaskNamespace("/tasks"))
        NodeTaskNamespace.node_worker_ref = self

        self.socketIO.connect(
            url=f"{self.client.host}:{self.client.port}",
            headers=self.client.headers,
            wait=False,
        )

        # Log the outcome
        i = 0        

        while not self.socketIO.connected:
            if i > TIME_LIMIT_INITIAL_CONNECTION_WEBSOCKET:
                self.log.critical(
                    "Could not connect to the websocket channels, do you have a "
                    "slow connection?"
                )
                exit(1)
            self.log.debug("Waiting for socket connection...")
            time.sleep(1)
            i += 1

        self.log.info(
            f"Connected to host={self.client.host} on port=" f"{self.client.port}"
        )

        self.log.debug(
            "Starting thread to ping the server to notify this node is online."
        )
        self.socketIO.start_background_task(self.__socket_ping_worker)

    def __socket_ping_worker(self) -> None:
        """
        Send ping messages periodically to the server over the socketIO
        connection to notify the server that this node is online
        """
        # Wait for the socket to be connected to the namespaces on startup
        time.sleep(5)

        while True:
            try:
                if self.socketIO.connected:
                    self.socketIO.emit("ping", namespace="/tasks")
                else:
                    self.log.debug("SocketIO is not connected, skipping ping")
            except Exception:
                self.log.exception("Ping thread had an exception")
            
            PING_INTERVAL_SECONDS = 60
            
            # Wait before sending next ping
            time.sleep(PING_INTERVAL_SECONDS)

    def cleanup(self) -> None:
        # TODO add try/catch for all cleanups so that if one fails, the others are
        # still executed

        if hasattr(self, "socketIO") and self.socketIO:
            self.socketIO.disconnect()
        """
        TODO include these if apply:        
        if hasattr(self, "vpn_manager") and self.vpn_manager:
            self.vpn_manager.exit_vpn()
        if hasattr(self, "ssh_tunnels") and self.ssh_tunnels:
            for tunnel in self.ssh_tunnels:
                tunnel.stop()
        if hasattr(self, "_Node__docker") and self.__docker:
            self.__docker.cleanup()
        """

        self.log.info("Bye!")


    def sync_task_queue_with_server(self) -> None:
        """Get all unprocessed tasks from the server for this node."""
        assert self.client.cryptor, "Encrpytion has not been setup"

        # request open tasks from the server
        task_results = self.client.run.list(state="open", include_task=True)
        self.log.debug("task_results: %s", task_results)

        # add the tasks to the queue
        self.__add_tasks_to_queue(task_results)
        self.log.info("Received %s tasks", self.queue._qsize())


    def __add_tasks_to_queue(self, task_results: list[dict]) -> None:
        """
        Add a task to the queue.

        Parameters
        ----------
        taskresult : list[dict]
            A list of dictionaries with information required to run the
            algorithm
        """
        for task_result in task_results:
            try:
                if not self.__docker.is_running(task_result["id"]):
                    self.queue.put(task_result)
                else:
                    self.log.info(
                        f"Not starting task {task_result['task']['id']} - "
                        f"{task_result['task']['name']} as it is already "
                        "running"
                    )
            except Exception:
                self.log.exception("Error while syncing task queue")


    def share_node_details(self) -> None:
        """
        Share part of the node's configuration with the server.

        This helps the other parties in a collaboration to see e.g. which
        algorithms they are allowed to run on this node.
        """
        # check if node allows to share node details, otherwise return
        if not self.config.get("share_config", True):
            self.log.debug(
                "Not sharing node configuration in accordance with "
                "the configuration setting."
            )
            return

        config_to_share = {}

        encryption_config = self.config.get("encryption")
        if encryption_config:
            if encryption_config.get("enabled") is not None:
                config_to_share["encryption"] = encryption_config.get("enabled")

        # share node policies (e.g. who can run which algorithms)
        policies = self.config.get("policies", {})
        config_to_share["allowed_algorithms"] = policies.get(
            "allowed_algorithms", "all"
        )
        if policies.get("allowed_users") is not None:
            config_to_share["allowed_users"] = policies.get("allowed_users")
        if policies.get("allowed_organizations") is not None:
            config_to_share["allowed_orgs"] = policies.get("allowed_organizations")

        # share node database labels, types, and column names (if they are
        # fixed as e.g. for csv file)
        labels = []
        types = {}
        col_names = {}
        for db in self.config.get("databases", []):
            label = db.get("label")
            type_ = db.get("type")
            labels.append(label)
            types[f"db_type_{label}"] = type_
            if type_ in ("csv", "parquet"):
                col_names[f"columns_{label}"] = self.__docker.get_column_names(
                    label, type_
                )
        config_to_share["database_labels"] = labels
        config_to_share["database_types"] = types
        if col_names:
            config_to_share["database_columns"] = col_names

        self.log.debug("Sharing node configuration: %s", config_to_share)
        self.socketIO.emit("node_info_update", config_to_share, namespace="/tasks")        

if __name__ == '__main__':

    node = NodePod()
    print("Success")
    


