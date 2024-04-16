from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException
from vantage6.common.task_status import TaskStatus
from typing import Tuple, List
from vantage6.common.task_status import TaskStatus, has_task_failed
from vantage6.common import logger_name
from typing import NamedTuple
from enum import Enum
import re
import os
import yaml
import logging
import time



logging.basicConfig(level=logging.INFO)
log = logging.getLogger(logger_name(__name__))

class Result(NamedTuple):
    """
    Data class to store the result of the docker image.

    Attributes
    ----------
    run_id: int
        ID of the current algorithm run
    logs: str
        Logs attached to current algorithm run
    data: str
        Output data of the algorithm
    status_code: int
        Status code of the algorithm run
    """

    run_id: int
    task_id: int
    logs: str
    data: str
    status: str
    parent_id: int | None


class ContainerManager:

    #v6-node configuration entries
    v6_config: dict

    log = logging.getLogger(logger_name(__name__))


    def __init__(self):

        global v6_config
            
        #minik8s config
        home_dir = os.path.expanduser('~')
        kube_config_file_path = os.path.join(home_dir, '.kube', 'config')

        #Instanced within the host
        if os.path.exists(kube_config_file_path):
            #default microk8s
            config.load_kube_config(kube_config_file_path)

            with open('node_config.yaml', 'r') as file:
                v6_config = yaml.safe_load(file)

            log.info(f'v6 settings:{v6_config}')
            log.info('Using microk8s host configuration')            
        
        #Instanced within a pod
        elif os.path.exists('/app/.kube/config'):
            #Default mount location defined on POD configuration                
            config.load_kube_config('/app/.kube/config')            
            with open('/app/.v6node/node_config.yaml', 'r') as file:
                v6_config = yaml.safe_load(file)
            print(f'v6 settings:{v6_config}')
            print('Microk8s using configuration file bind to a POD')            
        
        # before a task is executed it gets exposed to these policies
        self._policies = self._setup_policies(config)

        # K8S Batch API instance
        self.batch_api = client.BatchV1Api()
        # K8S Core API instance
        self.core_api = client.CoreV1Api()

        


    def version(self)->str:
        return "0"


    def _setup_policies(self, config: dict) -> dict:
        """
        Set up policies for the node.

        Parameters
        ----------
        config: dict
            Configuration dictionary

        Returns
        -------
        dict
            Dictionary with the policies
        """
        policies = v6_config.get("policies", {})
        if not policies or not policies.get("allowed_algorithms"):
            self.log.warning(
                "No policies on allowed algorithms have been set for this node!"
            )
            self.log.warning(
                "This means that all algorithms are allowed to run on this node."
            )
        return policies



    def run(self, run_id: int, task_info: dict, image: str,
            docker_input: bytes, tmp_vol_name: str, token: str,
            databases_to_use: list[str]
        )->tuple[TaskStatus, list[dict] | None]:
        """
        Checks if docker task is running. If not, creates DockerTaskManager to
        run the task

        Parameters
        ----------
        run_id: int
            Server run identifier
        task_info: dict
            Dictionary with task information *** Includes parent-algorithm id
        image: str
            Docker image name
        docker_input: bytes
            Input that can be read by docker container
        tmp_vol_name: str
            Name of temporary docker volume assigned to the algorithm
        token: str
            Bearer token that the container can use
        databases_to_use: list[str]
            Labels of the databases to use

        Returns
        -------
        TaskStatus, list[dict] | None
            Returns a tuple with the status of the task and a description of
            each port on the VPN client that forwards traffic to the algorithm
            container (``None`` if VPN is not set up).
        """

        #Usage context: https://github.com/vantage6/vantage6/blob/b0c961c8a060d9ea656e078e685a8e7d0560ef44/vantage6-node/vantage6/node/__init__.py#L349


        # Verify that an allowed image is used
        if not self.is_docker_image_allowed(image, task_info):
            msg = f"Docker image {image} is not allowed on this Node!"
            self.log.critical(msg)
            return TaskStatus.NOT_ALLOWED, None

        # Check that this task is not already running
        if self.is_running(run_id):
            self.log.warn("Task is already being executed, discarding task")
            self.log.debug(f"run_id={run_id} is discarded")
            return TaskStatus.ACTIVE, None

        str_run_id = str(run_id)

        task_args = list(task_info.values())

        _volumes, _volume_mounts = self._create_volume_mounts(str_run_id)

        container = client.V1Container(
                            name=str_run_id,
                            image=image,
                            #standard container command line
                            command=["python","app.py"],
                            args=task_args,
                            tty = True,
                            #args=["/app/data/output.txt","1000","5"],
                            volume_mounts=_volume_mounts
                        )


        # Define the job
        job = client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=client.V1ObjectMeta(name=str_run_id),
            spec=client.V1JobSpec(
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(labels={"app": str_run_id}),
                    spec=client.V1PodSpec(
                        containers=[container],
                        volumes=_volumes,
                        restart_policy="Never",
                    ),
                ),
                backoff_limit=1,
            ),
        )

        self.batch_api.create_namespaced_job(namespace="v6-jobs", body=job)

        #Based on
        #https://stackoverflow.com/questions/57563359/how-to-properly-update-the-status-of-a-job
        #https://kubernetes.io/docs/concepts/workloads/controllers/job/#pod-backoff-failure-policy

        """
        Pending, Running, Succeeded, Failed, Unknown
        Kubernetes will automatically retry the job N times (backoff_limit value above). According
        to the Pod's backoff failure policy, it will have a failed status only after the last failed retry.
        """
        
        interval = 1
        timeout = 60

        start_time = time.time()
        
        #the create_namespaced_job() method is asynchronous, so evaluating the pod execution status
        #requires first polling the K8S API until the new job/POD shows up.
        while True:
            pods = self.core_api.list_namespaced_pod(namespace="v6-jobs", label_selector=f"app={run_id}")
            if pods.items:
                #The container was created. Now wait until it reports either an 'active' or 'failed' status
                # Pod-creation -> Pending -> Running -> Failed
                #What should be done in the case of a timeout while checking this?
                self.log.info(f"{len(pods.items)} Job POD with label app={run_id} created successfuly on v6-jobs namespace. Waiting until it has a (k8S) running state.")
                status = self.__wait_until_pod_running(f"app={run_id}")
                self.log.info(f"Job POD with label app={run_id} is now on a running state.")

                return status, None
                
            elif time.time() - start_time > timeout:
                self.log.error(f"Timeoit while waiting Job POD with label app={run_id} to report a running state.")
                #The job could still start after the timeout
                return TaskStatus.UNKNOWN_ERROR
                
            else:            
                time.sleep(interval)


    def __wait_until_pod_running(self,run_id_label_selector:str)->TaskStatus:
        """
        This method execution gets blocked until the POD with the given label selector (which corresponds
        to the task's 'run_id') reports a 'Running' state. This method is expected to be used right
        after the job's creation request. Once this request is done, the POD has to initial statuses:
        'Pending' and the 'Running'. 

        Returns:
        Either TaskStatus.ACTIVE when the POD status is 'Running' (the POD container was kicked off), 
                          or TaskStatus.UNKNOWN_ERROR if there is a timeout while waiting for
                           reaching such 'Running' status (due to other errors)
        

        *Question: where are the failures detected on v6? : error code of command

        Wait for the POD to start
                                                              / Succeded
        Potential statuses of a Job POD: Pending -> Running - - Failed
                                                              \ Unknown
        """

        # Start watching for events on the pod
        w = watch.Watch()
        

        for event in w.stream(func=self.core_api.list_namespaced_pod,
                            namespace="v6-jobs",
                            label_selector=run_id_label_selector,
                            timeout_seconds=120):
            
            pod_phase = event['object'].status.phase

            if pod_phase == "Running":
                w.stop()
                return TaskStatus.ACTIVE
                            
        #This point is reached after timeout 
        return TaskStatus.UNKNOWN_ERROR    
    

    def _create_volume_mounts(self,run_id:str)->Tuple[List[client.V1Volume],List[client.V1VolumeMount]]:
        """
        Define all the mounts required by the algorithm/job: input files (csv), output, and temporal data
        """
        volumes :List[client.V1Volume] = []
        vol_mounts:List[client.V1VolumeMount] = []
        

        # Define a volume for input/output for this run. Following v6 convention, this is a volume bind to a
        # sub-folder created for the given run_id (i.e., the content will be shared by all the
        # algorithm instances of the same 'run' within this node).
        io_volume = client.V1Volume(
            name=f'task-{run_id}-output',
            host_path=client.V1HostPathVolumeSource(path=os.path.join(v6_config['task_dir'],run_id,'output'))
        )
        volumes.append(io_volume)

        # Volume mount path for i/o data (/app is the WORKDIR path of v6-node's container)
        io_volume_mount = client.V1VolumeMount(
            #standard containers volume mount location
            name=f'task-{run_id}-output',
            mount_path='/app/output'            
        )

        vol_mounts.append(io_volume_mount)

        """
         Note: Volume-claims could be used insted of 'host_path' volumes to decouple vantage6 file
          management from the storage provider (NFS, GCP, etc). However, persitent-volumes (from which 
          volume-claims are be created), present a risk when used on local file systems. In particular,
          if two VC are created from the same PV, both would end sharing the same files. 

          Define the volume for temporal data 
          tmp_volume = client.V1Volume(
            name=f'task-{str_run_id}-tmp',
            persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(claim_name=tmp_vol_name)
          )
        """

        # Define the volume for temporal data 
        tmp_volume = client.V1Volume(
            name=f'task-{run_id}-tmp',
            host_path=client.V1HostPathVolumeSource(path=os.path.join(v6_config['task_dir'],run_id,'tmp')),
        )

        volumes.append(tmp_volume)

        # Define the volume mount for temporary data
        tmp_volume_mount = client.V1VolumeMount(
            #standard containers volume mount location
            mount_path='/app/tmp',
            name=f'task-{run_id}-tmp'
        )

        vol_mounts.append(tmp_volume_mount)

        # Bind-mount all the CSV files (read only) defined on the configuration file 
        csv_input_files = list(filter(lambda o: (o['type']=='csv'), v6_config['databases']))

        for csv_input in csv_input_files:

            _volume = client.V1Volume(
                name=f"task-{run_id}-input-{csv_input['label']}",
                host_path=client.V1HostPathVolumeSource(csv_input['uri']),
            )

            volumes.append(_volume)

            _volume_mount = client.V1VolumeMount(            
                mount_path=f"/app/input/csv/{csv_input['label']}",
                name=f"task-{run_id}-input-{csv_input['label']}",
                read_only=True
            )

            vol_mounts.append(_volume_mount)

        return volumes,vol_mounts
    

    
    def create_volume(self,volume_name:str)->None:
        """
        This method creates a persistent volume through volume claims. However, this method is not being
        used yet, as using only host_path volume binds seems to be enough and more convenient 
        (see details on _create_volume_mounts) - this is to be discussed
        """
        
        """
        @precondition: at least one persistent volume has been provisioned in the (single) kubernetes node
        
        """

        is_valid_vol_name = re.search("[a-z0-9]([-a-z0-9]*[a-z0-9])?(\\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*",volume_name)

        if not is_valid_vol_name:
            #TODO custom exceptions to decouple codebase from kubernetes
            raise Exception(f'Invalid volume name; {volume_name}')            

        
        #create a persistent volume claim with the given name
        pvc = client.V1PersistentVolumeClaim(
            api_version='v1',
            kind='PersistentVolumeClaim',
            metadata=client.V1ObjectMeta(name=volume_name),
            spec=client.V1PersistentVolumeClaimSpec(
                storage_class_name='manual',
                access_modes=['ReadWriteOnce'],
                resources=client.V1ResourceRequirements(
                    #TODO Storage quota to be defined in system properties
                    requests={'storage': '1Gi'}
                )
            )
        )
        
        """
        If the volume was not claimed with the given name yet, there won't be exception.
        If the volume was already claimed with the same name, (which should not make the function to fail), 
            the API is expected to return an 409 error code.
        """
        try:
            self.core_api.create_namespaced_persistent_volume_claim('v6-jobs',body=pvc)
        except client.rest.ApiException as e:
            if e.status != 409:
                #TODO custom exceptions to decouple codebase from kubernetes
                raise Exception(f"Unexpected kubernetes API error code {e.status}") from e



    def _create_host_path_persistent_volume(self,path:str)->None:
        """
        Programatically creates a persistent volume (in case it is needed for creating a
        volume claim). Just for reference, not currently being used.
        """
        pv = client.V1PersistentVolume(
            metadata=client.V1ObjectMeta(name='task-pv-volume', labels={'type': 'local'}),
            spec=client.V1PersistentVolumeSpec(
                storage_class_name='manual',
                capacity={'storage': '10Gi'},
                access_modes=['ReadWriteOnce'],
                host_path=client.V1HostPathVolumeSource(path=path)
            )
        )
        self.core_api.create_persistent_volume(body=pv)


    
    def is_docker_image_allowed(self, docker_image_name: str, task_info: dict) -> bool:
        """
        Checks the docker image name.

        Against a list of regular expressions as defined in the configuration
        file. If no expressions are defined, all docker images are accepted.

        Parameters
        ----------
        docker_image_name: str
            uri to the docker image
        task_info: dict
            Dictionary with information about the task

        Returns
        -------
        bool
            Whether docker image is allowed or not
        """
        
        #TODO use original v6 implementation
        
        return True
        
    

    
    def is_running(self, run_id: int) -> bool:
        """
        
        Check if a container is already running for <run_id>.

        Parameters
        ----------
        run_id: int
            run_id of the algorithm container to be found

        Returns
        -------
        bool
            Whether or not algorithm container is running already
        """
        
        """
        To be discussed:
        Potential statuses of a Job POD: Pending, Running, Succeeded, Failed, Unknown
        This method is used locally to check whether a given task was already executed. In which case does
        happen?
        Given the above What would be the expected return value if the task was already completed or failed?
        
        """
        pods = self.core_api.list_namespaced_pod(namespace="v6-jobs", label_selector=f"app={run_id}")
        if pods.items:
            return True
        else:
            return False


    def __deleteme_status(self, run_id: int) -> bool:
        """
        
        Check if a container is already running for <run_id>.

        Parameters
        ----------
        run_id: int
            run_id of the algorithm container to be found

        Returns
        -------
        bool
            Whether or not algorithm container is running already
        """
        print (f"Status of {run_id}")

        try:
            # Get the pod details
            pods = self.core_api.list_namespaced_pod(namespace="v6-jobs", label_selector=f"app={run_id}")
            if pods.items:
                pod = pods.items[0]
                # Access the 'app' label from the pod's metadata
                app_label = pod.metadata.labels.get('app')
                print(f"Pod {pod.metadata.name} has 'app' label: {app_label}")
                print(f"Pod {str(run_id)} status: {pod.status.phase}")   
                print(type(pod.status.phase)) 
            else:
                print("No pods found with the specified label.")            
            
            


        except client.ApiException as e:
            print(f"Exception when calling CoreV1Api->read_namespaced_pod: {e}")

        #job_pods = self.core_api.list_namespaced_pod("v6-jobs")
        #print(type(job_pods))
        #print(job_pods)
        return True


    def get_result(self) -> Result:    
        """
        * Original description:
            Returns the oldest (FIFO) finished docker container.
            This is a blocking method until a finished container shows up. Once the
            container is obtained and the results are read, the container is
            removed from the docker environment.

        * Proposed (more accurate) description:
            proposed name: process_next_completed_job
            Process the next completed pod/jobs (can be either finsihed or failed), as soon any of these is shown (not necesarily FIFO):

                When failed-job found (after N attempts handled by kubernetes (N = job backoffLimit) ) => 
                    Cleanup POD/containers
                    return Result with:
                        TaskStatus.CRASHED
                        Log error: logs = self.container.logs().decode("utf8")

                When Successful POD found=>
                    return Result with:
                        TaskStatus.COMPLETED
                        Result file content
                        Log: report status: logs = self.container.logs().decode("utf8")


                                                              / Succeded
        Potential statuses of a Job POD: Pending -> Running - - Failed
                                                              \ Unknown

        """        
        jobs = []

        #wait until there is at least one completed job available (successful or failed)
        #other statuses (pending/running/unknown) are ignored (for the moment)
        
        completed_job = False

        while not completed_job:
            jobs = self.batch_api.list_namespaced_job("v6-jobs")
            
            if not jobs:
                time.sleep(1)
            else:
                for job in jobs.items:

                    if job.status.succeeded:
                        job_id = job.metadata.name
                        self.log.info(f"Found a completed job with a (k8s) Succeded status: {job_id}. Returning result with v6-COMPLETED status")          

                        #If executing from POD, use convention '/app/tasks
                        #output_file = os.path.join('/app/tasks', job_id, 'output/avg.txt')x
                        succeded_job_output_file = os.path.join(v6_config['task_dir'],job_id,'output/avg.txt')

                        self.log.info(f"Reading data generated by job {job.metadata.name} at {succeded_job_output_file}")          

                        #if executing from HOST, use path given in v6 config file
                        #output_file = os.path.join('/app/tasks', job_id, 'output/avg.txt')

                        with open(succeded_job_output_file, "rb") as fp:
                            results = fp.read()
                                
                        #get PODs logs 
                        pod_tty_output = self.__get_job_pod_logs(job_id=job_id,namespace="v6-jobs")

                        #destroy job and related POD(s)
                        self.log.info(f"Cleaning up kubernetes Job {job.metadata.name} (job id = {job_id}) and related PODs")
                        self.batch_api.delete_namespaced_job(name=job_id, namespace="v6-jobs")
                        self.__delete_job_related_pods(job_id=job_id,namespace="v6-jobs")

                        result = Result(
                                run_id=-1,
                                task_id=job_id,
                                logs=pod_tty_output,  
                                data=results,   
                                status=TaskStatus.COMPLETED,
                                parent_id=-1 #get_parent_id(task_dict: dict) will be used
                            )
                        completed_job = True    
                    
                    elif job.status.failed:
                        job_id = job.metadata.name
                                                
                        self.log.info(f"Found a completed job with a (k8s) Failed status: {job.metadata.name} (job_id = {job_id}). Returning result with v6-CRASHED status")
                        
                        #get PODs logs 
                        pod_tty_output = self.__get_job_pod_logs(job_id=job_id,namespace="v6-jobs")

                        #destroy POD
                        #Should the POD be cleaned up in this case too?
                        self.log.info(f"Cleaning up container & job POD {job.metadata.name} / {job_id}")
                        self.batch_api.delete_namespaced_job(name=job_id, namespace="v6-jobs")
                        self.__delete_job_related_pods(job_id=job_id,namespace="v6-jobs")

                        result = Result(
                                run_id=-1,
                                task_id=job_id,
                                logs=pod_tty_output,  
                                data=b"",   
                                status=TaskStatus.CRASHED,
                                parent_id=-1 #get_parent_id(task_dict: dict) will be used
                            )    
                        completed_job = True
                    
        return result




    def __get_job_pod_logs(self,job_id:str,namespace="v6-jobs") -> List[str]:
        """"
        Get the logs generated by the PODs created by a job.
        
        If there are multiple PODs created by the job (e.g., due to multiple failed execution attempts -see 
        backofflimit setting-) all the POD logs are merged as one.
        """        

        pods_tty_logs = []

        job_selector = f"job-name={job_id}"
        job_pods_list = self.core_api.list_namespaced_pod(namespace, label_selector=job_selector)

        for job_pod in job_pods_list.items:
            pods_tty_output = f"LOGS of POD {job_pod.metadata.name} (created by job {job_id}) \n"
            self.log.info(f"Getting logs from POD {job_pod.metadata.name}, created by job {job_id}")            

            pods_tty_logs.append(self.core_api.read_namespaced_pod_log(job_pod.metadata.name, "v6-jobs"))
            
        return pods_tty_logs
        

    def __delete_job_related_pods(self,job_id,namespace="v6-job"):
        """
        Deletes all the PODs created by a Kubernetes job in a given namespace
        """
        job_selector = f"job-name={job_id}"
        job_pods_list = self.core_api.list_namespaced_pod(namespace, label_selector=job_selector)
        for job_pod in job_pods_list.items:
            try:
                self.log.info(f"Deleting pod {job_pod.metadata.name} of job {job_id}")
                self.core_api.delete_namespaced_pod(job_pod.metadata.name, namespace)
                self.log.info(f"Pod {job_pod.metadata.name} of job {job_id} deleted.")
            except ApiException as e:
                self.log.warn(f"Warning: POD {job_pod.metadata.name} of job {job_id} couldn't be deleted.")



    #def cleanup_tasks(self) -> list[KilledRun]:
        """
        Stop all active tasks

        Returns
        -------
        list[KilledRun]:
            List of information on tasks that have been killed
        """


    #def cleanup(self) -> None:
        """
        Stop all active tasks and delete the isolated network

        Note: the temporary docker volumes are kept as they may still be used
        by a parent container
        """
        # note: the function `cleanup_tasks` returns a list of tasks that were
        # killed, but we don't register them as killed so they will be run
        # again when the node is restarted

   



    #def login_to_registries(self, registries: list = []) -> None:
        """
        Login to the docker registries

        Parameters
        ----------
        registries: list
            list of registries to login to
        """


    #def link_container_to_network(self, container_name: str, config_alias: str) -> None:
        """
        Link a docker container to the isolated docker network

        Parameters
        ----------
        container_name: str
            Name of the docker container to be linked to the network
        config_alias: str
            Alias of the docker container defined in the config file
        """


    #def kill_selected_tasks(
    #    self, org_id: int, kill_list: list[ToBeKilled] = None
    #) -> list[KilledRun]:


    #def kill_tasks(
    #    self, org_id: int, kill_list: list[ToBeKilled] = None
    #) -> list[KilledRun]:
        """
        Kill tasks currently running on this node.

        Parameters
        ----------
        org_id: int
            The organization id of this node
        kill_list: list[ToBeKilled] (optional)
            A list of info on tasks that should be killed. If the list
            is not specified, all running algorithm containers will be killed.

        Returns
        -------
        list[KilledRun]
            List of dictionaries with information on killed tasks
        """


    #def get_column_names(self, label: str, type_: str) -> list[str]:
        """
        Get column names from a node database

        Parameters
        ----------
        label: str
            Label of the database
        type_: str
            Type of the database

        Returns
        -------
        list[str]
            List of column names
        """
