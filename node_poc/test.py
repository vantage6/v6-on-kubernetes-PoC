from container_manager import ContainerManager


cm = ContainerManager()


# When volumes are being destroyed? https://github.com/vantage6/vantage6/blob/a759f540c731a19d351c82b414b729b303ad7aa3/vantage6-node/vantage6/node/docker/docker_manager.py#L357

#precondition: at least one persistent volume has been provisioned in the (single) kubernetes node
#cm.create_volume('volume-alg-zzz')


cm.run(run_id=123456,
       image='hectorcadavid/avg-alg-x86',
       tmp_vol_name='',
       task_info={"arg1":"/app/input/csv/default","arg2":"Age","arg3":"/app/output/avg.txt"},
       docker_input=None,databases_to_use=None,token=None)


#cm.run(run_id=666666,
#       image='hectorcadavid/dummy_volume_reader_x86',
#       tmp_vol_name='volume-alg-zzz',
#       task_info={"arg1":"/app/data/output.txt","arg2":"5"},
#       docker_input=None,databases_to_use=None,token=None)



