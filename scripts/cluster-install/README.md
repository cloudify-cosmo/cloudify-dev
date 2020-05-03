# Cluster install script

## Usage

### Install cluster

The cluster-install script has two modes:
1. Installing the cluster using existing VMs. 
1. Create the necessary Openstack environment (VMs, security group) and install the cluster using it.   

##### Install cluster using existing VMs
1. Make sure the VMs follow the [prerequisites](https://docs.cloudify.co/5.0.5/install_maintain/installation/prerequisites/#cloudify-cluster).
1. Make sure all the requirements from the `requirements.txt` file are satisfied. 
1. Fill in the config_env.yaml file. Make sure to fill in the existing_vms list 
according to the number of instances of each type: manager / postgresql / rabbitmq. 
E.g. if the cluster should include 3 Managers, then in the config_env.yaml under `number_of_instances`, there should be `manager:3`
and under `existing_vms` there should be 3 items with `instance_type: 'manager'`. 
**Notice:** You must specify a VM for a jump-host.
1. In case you are using an existing security group, you can specify its ID in the config_env.yaml under `existing_security_group_id`.
1. You don't need to fill in the `Openstack connection configuration` part in the config_env.yaml
1. Run the command `python install.py --config-path <config_env.yaml path>`.
1. Wait until the cluster is fully installed - should be around 20 minutes. 
1. In case you want to use local-host, SCP the ca.pem certificate from the jump-host to your local host.
This can be done with the following command `scp -i ~/.ssh/jump_key.pem <ssh-user>@<jump-host-ip>:/tmp/install_cluster/certs/ca.pem <destination-local-path>`.
1. In order to use one of the managers in the CLI you can use the following command:
`cfy profiles use -u admin -p admin -t default_tenant --ssl --rest-certificate <ca.pem-path> -s <ssh-user> <public-ip>`.  
The `ca.pem-path` on the jump-host is: `/tmp/install_cluster/certs/ca.pem`
Switch the `<public-ip>` with the public-ip of one of the managers or the load balancer,
and the `<ssh-user>` with the ssh user on the host machine, e.g. centos.

##### Create the Openstack environment and install cluster
1. Before installation, please make sure you have a key and network ready on Openstack. 
1. Download the OpenStack RC file from Openstack under Access & Security / API access.
1. Fill in the config_env.yaml file according to the RC file. Make sure to fill in the `Openstack connection configuration` part and leave the `existing_vms` value blank (None).   
**NOTICE:** In case you think the manager will need a big memory resource, e.g. for a big snapshot restore - use `flavor_name: m1.medium`. 
1. Run the command `python install.py --config-path <config_env.yaml path>`.
1. Make sure all the requirements from the `requirements.txt` file are satisfied. 
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
**Note:** This is only relevant if the script created the Openstack environment. 
In order to delete the created cluster, i.e. revert the Openstack environment to 
its pre installation state, run the command `python clean-openstack.py 
--config-path <config_env.yaml path> --environment-ids-path <environment_ids.yaml path>`.
This will delete all installed servers, their associated floating IPs and the cluster security group. 
