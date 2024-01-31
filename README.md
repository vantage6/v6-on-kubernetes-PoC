

Simplified v6-node

- Work based on the configuration file
- 



1. Setup microk8s on [Linux](https://ubuntu.com/tutorials/install-a-local-kubernetes-with-microk8s#1-overview). It can be installed on [Windows](https://microk8s.io/docs/install-windows), but this PoC has been tested only on Ubunty environments.

2. [optional] run the kubernetes dashboard

```
microk8s dashboard-proxy
```
copy the key


2. Edit the configuration file (the settings not yet being used are commented)

    ````
    task_dir:
    databases:
    ```

2. Run the 'dummy-server'. A simple socket.io server the node is subscribet to when launched. 

3. Setting up and launching the 'node' as a Pod deployment.

3.1.update the node_pod_config.yaml to set the absolute path of the kubernetes configuration file (kube-config-file), and the absolute path of the v6 config file (the one included in this repo)

```
volumes:
 - name: task-files-root
   hostPath:
     path: /tmp/tasks
 - name: kube-config-file
   hostPath:
     path: /home/hcadavid/.kube/config   
 - name: v6-node-config-file
   hostPath:
     path: /home/hcadavid/k8s/v6-Kubernetes-PoC/node_poc/node_config.yaml
```
 

3. from the node_poc

```
kubectl apply -f node_pod_config.yaml
```

4. Check the POD on the dashboard - https://<hostname>:10443

5. send a request to the node by posting an event on the socketio server. Use the code snipped command-emitter.py

6. Check the files