# Cluster install script

## Usage

### Install cluster
These are the steps to install and use a Cloudify Manager cluster on Openstack:
1. Download the OpenStack RC file from Openstack under Access & Security / API access.
1. Fill in the config_env.yaml file according to the RC file.
1. Run the command `python install.py --config-path <config_env.yaml path>`
1. Wait until the cluster is fully installed - should be around 20 minutes. 
1. After the creation of the Openstack environment a file named `environment_ids.yaml` will 
be created. This file includes the IDs of the running VMs and of the security-group for future use of cleaning the environment.  
1. In case of a failure in the process, the Openstack environment will not be cleaned automatically.
Alternatively, if you want to clean the environment, you can pass the flag `--clean-on-failure` to the `install` command.  
1. In order to use one of the managers in the CLI you can use the following command:
`cfy profiles use -u admin -p admin -t default_tenant --ssl --rest-certificate /tmp/install_cluster/certs/ca.crt -s <ssh-user> <public-ip>`.
Switch the `<public-ip>` with the public-ip of one of the managers or the load balancer,
and the `<ssh-user>` with the ssh user on the host machine, e.g. centos.  


### Delete cluster
In order to delete the created cluster, i.e. revert the Openstack environment to 
its pre installation state, run the command `python clean-openstack.py 
--config-path <config_env.yaml path> --environment-ids-path <environment_ids.yaml path>`.
This will delete all installed servers, their associated floating IPs and the cluster security group. 
