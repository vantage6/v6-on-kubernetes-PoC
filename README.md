# vantage6 on Kubernetes proof of concept

This repository contains a proof of concept for refactoring the Node component of Vantage6, particularly focusing on how it handles containerized algorithms.

[![IMAGE ALT TEXT HERE](https://img.youtube.com/vi/3J_fq4cn-Ds/0.jpg)](https://www.youtube.com/watch?v=3J_fq4cn-Ds)


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

The following diagram depicts the alternative K8S-based architecture envisioned for the v6 nodes:

![](img/containers-POC.drawio.png)

The work on this envisioned architecture involves two separate projects included in this repository:

### Architecture proof of concept

This is an implementation of a simplified version of the vantage6 client/server architecture. It is intended to be used to perform experiments for making design decisions (being the integration with K8S the most important one) without dealing with the complex V6 codebase.

[Architecture proof of concept guidelines](node_poc/node_poc.md)


### Integration proof of concept

An implementation of a V6 node intended to work as a regular (Docker-based) V6 node, but working with a K8S cluster under the hood. It is based and built on top of the experiments made with the architecture proof of concept.

[Integration proof of concept guidelines](integration_poc/integration_poc.md)



