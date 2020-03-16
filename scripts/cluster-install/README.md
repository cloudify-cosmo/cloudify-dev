# Cluster install script

## Usage

### Install cluster
These are the steps to install and use a Cloudify Manager cluster on Openstack:

1. Before installation, please make sure you have a key and network ready on Openstack. 
1. Download the OpenStack RC file from Openstack under Access & Security / API access.
1. Fill in the config_env.yaml file according to the RC file.  
**NOTICE:** In case you think the manager will need a big memory resource, e.g. for a big snapshot restore - use `flavor_name: m1.medium`.  
1. Run the command `python install.py --config-path <config_env.yaml path>`
1. Wait until the cluster is fully installed - should be around 20 minutes. 
1. During the creation of the Openstack environment a file named `environment_ids.yaml` will 
be created. This file includes the IDs of the running VMs and of the security-group for future use of cleaning the environment.  
1. In case of a failure in the process, the Openstack environment will not be cleaned automatically.
Alternatively, if you want to clean the environment, you can pass the flag `--clean-on-failure` to the `install` command.  
1. In case you want to use local-host, SCP the ca.pem certificate from the jump-host to your local host.
This can be done with the following command `scp -i ~/.ssh/jump_key.pem <ssh-user>@<jump-host-ip>:/tmp/install_cluster/certs/ca.pem <destination-local-path>`.
1. In order to use one of the managers in the CLI you can use the following command:
`cfy profiles use -u admin -p admin -t default_tenant --ssl --rest-certificate <ca.pem-path> -s <ssh-user> <public-ip>`.  
The `ca.pem-path` on the jump-host is: `/tmp/install_cluster/certs/ca.pem`
Switch the `<public-ip>` with the public-ip of one of the managers or the load balancer,
and the `<ssh-user>` with the ssh user on the host machine, e.g. centos.  


### Delete cluster
In order to delete the created cluster, i.e. revert the Openstack environment to 
its pre installation state, run the command `python clean-openstack.py 
--config-path <config_env.yaml path> --environment-ids-path <environment_ids.yaml path>`.
This will delete all installed servers, their associated floating IPs and the cluster security group. 
