from kubernetes import client, config
from task_status import TaskStatus
from typing import Tuple, List
import re
import os
import yaml

class ContainerManager:

    #v6-node configuration entries
    v6_config: dict

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

            print(f'v6 settings:{v6_config}')
            print('Using microk8s host configuration')            
        
        #Instanced within a pod
        elif os.path.exists('/app/.kube/config'):
            #Default mount location defined on POD configuration                
            config.load_kube_config('/app/.kube/config')            
            with open('/app/.v6node/node_config.yaml', 'r') as file:
                v6_config = yaml.safe_load(file)
            print(f'v6 settings:{v6_config}')
            print('Microk8s using configuration file bind to a POD')            
        
        # K8S Batch API instance
        self.batch_api = client.BatchV1Api()
        # K8S Core API instance
        self.core_api = client.CoreV1Api()


    def version(self)->str:
        return 0


    def _create_host_path_persistent_volume(self,path:str)->None:
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



    """"
    This method won't be needed
    """
    def create_volume(self,volume_name:str)->None:

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
            self.core_api.create_namespaced_persistent_volume_claim('default',body=pvc)
        except client.rest.ApiException as e:
            if e.status != 409:
                #TODO custom exceptions to decouple codebase from kubernetes
                raise Exception(f"Unexpected kubernetes API error code {e.status}") from e




    def run(self, run_id: int, task_info: dict, image: str,
            docker_input: bytes, tmp_vol_name: str, token: str,
            databases_to_use: list[str]
        )->None:
            #) -> tuple[TaskStatus, list[dict] | None]:
        """
        Checks if docker task is running. If not, creates DockerTaskManager to
        run the task

        Parameters
        ----------
        run_id: int
            Server run identifier
        task_info: dict
            Dictionary with task information
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
                backoff_limit=4,
            ),
        )

        self.batch_api.create_namespaced_job(namespace="default", body=job)



    def _create_volume_mounts(self,run_id:str)->Tuple[List[client.V1Volume],List[client.V1VolumeMount]]:
        """
        Define all the mounts required by the algorithm/job: input files (csv), output, and temporal data
        """
        volumes :[client.V1Volume] = []
        vol_mounts:[client.V1VolumeMount] = []
        

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