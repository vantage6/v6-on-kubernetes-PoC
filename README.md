# vantage6 on Kubernetes proof of concept

This repository contains a proof of concept for refactoring the Node component of Vantage6, particularly focusing on how it handles containerized algorithms.

## About vantage6 and containers management

[vantage6](https://distributedlearning.ai/) is a federated learning platform designed to facilitate privacy-preserving analysis without sharing sensitive data. The current architecture involves a central server, nodes, and clients. Nodes are responsible for executing algorithms on local data and securely communicating the results back to the server.

Vantage6 Nodes currently depend on the Docker API for container management (i.e., pulling images, creating the containers, linking I/O data to the containerized algorithms, checking its status, etc), as illustrated in the diagram below.

![](img/v6-node-arch.drawio.png)



While Docker provides a robust environment for executing algorithms, [discussions within the community](https://github.com/bdh-generalization/requirements/issues/7) are calling for enabling support for alternative containerization technologies. 

The motivations for this include:

- In many cases, the computing infrastructure within many health institutions has these alternatives installed by default, with podman and singularity as prominent examples.
- These alternative containerization technologies follow an architectural approach that offers more security: they do not require a long-running daemon process with root privileges like Docker. They are, by design, rootless.
- The algorithm containerization should not be constrained to a single technology. Ideally, vantage6 should support multiple container formats and runtimes.

Based on the discussion on [the potential alternatives](https://github.com/bdh-generalization/requirements/issues/7#issuecomment-1852243535) for this, this project is aimed at exploring a transition from a Docker-API to a Kubernetes-centered one. This alternative architecture, which could be deployed either on an existing Kubernetes cluster, or on a local lightweight (yet production ready) Kubernetes server (e.g., [microk8s](https://microk8s.io/) and [k3s](https://k3s.io/)) would have as additional benefits:

- A Kubernetes-API centered architecture on the Node would allow -in principle- to run algorithms containerized with any CRI-complaint, and to co-exist within the same isolated network.
- A significant part of the container management complexity could be separated from the application (e.g., algorithms isolation, I/O volume mount permissions, 'self-healing', etc).
- The overall management and diagnostics process at runtime would be simplified by enabling the use of Kubernetes tools (e.g., [Dashboards](https://kubernetes.io/docs/tasks/access-application-cluster/web-ui-dashboard/))


## Proof of concept

vantage6 is a piece of software too complex to perform experiments on its core architecture. Therefore, exploring the feasibility of doing this major architectural change, and validating our current assumptions about it, requires a prototyped solution as a proof of concept.

This prototype reimplements the methods of vantage6's DockerManager class (on a new class called ContainerManager) using the Kubernetes API. Furthermore, it is based on the settings given by the current [vantage6 configuration file format](https://docs.vantage6.ai/en/main/node/configure.html) (the settings still not considered are under comments).

The other artifacts in this repository are below described:

- dummy-socketio-server: 
	- simple-sio-server: a minimalist (dummy) vantage6 server -just to publish the tasks the Node must perform.
	- command-emitter: script for publishing task descriptions in JSON format to the server (which are then collected and executed by the Node).


- node-poc: 
	- container_manager.py: the re-implementation of the methods of the original DockerManager, using the Kubernetes API.
	- node.py: a process that listens for requests published on the 'dummy server', and executes ContainerManager methods accordingly.
	
- avg_alg: 'dummy' algorithm using the I/O conventions used by the PoC.
  	

## Proof of concept status

- [x] Baseline code for experiments
- [x] Programmatically launching algorithms as job PODs, binding volumes to them, according to v6 configuration settings: ('task_dir') and ('databases').
- [x] Kubernetes configuration for launching the node as a POD deployment, giving it access to the host's Kubernetes configuration (so it can perform further operations on Kubernetes programmatically).
- [ ] Defining network isolation rules for the jobs as a NetworkPolicy resource.
- [ ] 


![](img/containers-POC.drawio.png)

## Setup (using microk8s)


1. Setup microk8s on [Linux](https://ubuntu.com/tutorials/install-a-local-kubernetes-with-microk8s#1-overview). It can be installed on [Windows](https://microk8s.io/docs/install-windows), but this PoC has been tested only on Ubuntu environments.

2. Setup and enable the Kubernetes dashboard [following the microk8s guidelines](https://microk8s.io/docs/addon-dashboard).

3. Edit the configuration file (the settings not yet being used are commented)

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





# Proof of Concept for Vantage6 Node Refactor

This repository contains a proof of concept for a potential architecture refactor for the Vantage6 platform, focusing specifically on the Node component and how it handles containerized algorithms.

## Overview

Vantage6 is a federated learning platform where Nodes execute algorithms on local data and communicate results to a central server. The Node component is complex, responsible for various tasks including algorithm execution, container isolation, and communication with other components [0][1].

## Objective

The goal of this project is to explore a change to the core aspect of how the Node component manages containerized algorithms. To ensure the stability of the entire platform, we will conduct experiments and validation on a simplified version of the Node component.

## Experiment Setup

We have set up a controlled environment to simulate the behavior of the Node component within the Vantage6 framework. This environment allows us to isolate and observe the effects of our proposed changes without impacting the live system.

## Proposed Changes

Our proposed changes aim to enhance the efficiency and security of the Node's algorithm handling process. We are considering improvements in areas such as container management, resource allocation, and error handling.

## Validation Process

Once the proposed changes are implemented, we will run a series of tests to validate their performance and compatibility with the existing Vantage6 architecture. These tests will cover various scenarios, including but not limited to:

- Load testing to assess performance under heavy computational load.
- Security testing to ensure data integrity and confidentiality.
- Integration testing to verify seamless interaction with other components.

## Getting Started

To experiment with the changes, clone this repository and follow the instructions in the `README.md` files within each subdirectory. You will need to have Python and Docker installed on your machine to run the simulations.

## Contributing

Contributions are welcome! If you find issues with the current implementation or have suggestions for improvements, please open an issue or submit a pull request.

## License

This project is licensed under the Apache License 2.0 - see the `LICENSE` file for details.

## Contact

For further inquiries, please contact the project maintainers at [insert contact email or link here].
