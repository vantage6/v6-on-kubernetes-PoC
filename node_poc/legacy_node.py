from vantage6.common.client.node_client import NodeClient
from threading import Thread
from vantage6.node import proxy_server
from vantage6.common.log import get_file_logger
from gevent.pywsgi import WSGIServer
from vantage6.common.exceptions import AuthenticationException
from vantage6.common import logger_name
import logging
import random
import requests
import time
import os


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

    
    def initialize(self) -> None:

        self.client = NodeClient(
                    host="https://v6-server.tail984a0.ts.net/",
                    port="443",
                    path="/api",
                )
        self.log.info(f"Connecting server: {self.client.base_path}")

        self.log.debug("Authenticating")
        self.authenticate()

        #TODO check/setup collaboration encryption status
        self.client.setup_encryption(None)

        # Thread for proxy server for algorithm containers, so they can
        # communicate with the central server.
        t = Thread(target=self.__proxy_server_worker, daemon=True)
        t.start()

        #TODO listen and process incoming messages
        self.log.info("Init complete")

    def __print_connection_error_logs(self):
        """Print error message when node cannot find the server"""
        self.log.warning("Could not connect to the server. Retrying in 10 seconds")

    def authenticate(self):
        """
        Authenticate with the server using the api-key from the configuration
        file. If the server rejects for any reason -other than a wrong API key-
        serveral attempts are taken to retry.
        """

        TIME_LIMIT_RETRY_CONNECT_NODE = 60
        SLEEP_BTWN_NODE_LOGIN_TRIES = 2

        api_key = "API"

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
        proxy_port = 7450

        # 'app' is defined in vantage6.node.proxy_server
        debug_mode = self.debug.get("proxy_server", False)
        if debug_mode:
            self.log.debug("Debug mode enabled for proxy server")
            proxy_server.app.debug = True
        proxy_server.app.config["SERVER_IO"] = self.client
        proxy_server.server_url = self.client.base_path

        # set up proxy server logging
        log_level = getattr(logging, self.config["logging"]["level"].upper())
        self.proxy_log = get_file_logger(
            "proxy_server", self.ctx.proxy_log_file, log_level_file=log_level
        )

        # this is where we try to find a port for the proxyserver
        for try_number in range(5):
            self.log.info("Starting proxyserver at '%s:%s'", proxy_host, proxy_port)
            http_server = WSGIServer(
                ("0.0.0.0", proxy_port), proxy_server.app, log=self.proxy_log
            )

            try:
                http_server.serve_forever()

            except OSError as e:
                self.log.info("Error during attempt %s", try_number)
                self.log.info("%s: %s", type(e), e)

                if e.errno == 48:
                    proxy_port = random.randint(2048, 16384)
                    self.log.warning("Retrying with a different port: %s", proxy_port)
                    os.environ["PROXY_SERVER_PORT"] = str(proxy_port)

                else:
                    raise

            except Exception as e:
                self.log.error("Proxyserver could not be started or crashed!")
                self.log.error(e)



if __name__ == '__main__':

    node = NodePod()
    


