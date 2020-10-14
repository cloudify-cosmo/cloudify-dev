# Replace Certificates script
The replace-certificates script enables users of Cloudify v5.0.5 to replace certificates on an All-In-One (AIO) manager or a cluster.  
**Important notes:**  
* The script doesn't take care of replacing certificates on agents.
* Since this script is dedicated for Cloudify v5.0.5 users, it uses Python2.
* Please keep all the script's files in the same directory. 

## Usage

### Replacing certificates on a cluster
The script `main.py` needs to run from one of the managers in the cluster or a host in the same network that has a Cloudify CLI installed.  
These are the steps in order to run it:
1. Fill in the `cluster_replace_certificates_config.yaml` file with the relevant information.
For each host, specify its host ip and new certificates' paths. A few notes:
    * For each host, either both certificate and key must be provided, or neither.
    * In order to replace a CA certificate, all related hosts' certificates need to be replaced as well. 
E.g. if you want to replace the RabbitMQ CA certificate, you will need to specify new certificates for all RabbitMQ hosts.
    * **Special case:** In case  of replacing the "postgresql_server" CA cert, the "manager" hosts' 
postgresql_client certificates need to be replaced as well.
1. Run the script using the CLI environment: `/opt/cfy/embedded/bin/python main.py`.
1. Optional flags:
    * `--config-path` - The path to the `replace_certificates_config.yaml`. The default path is 
    `./cluster_replace_certificates_config.yaml`.
    * `-v, --verbose` - Log more information.
    
### Replacing certificates on an AIO manager
The script `main.py` needs to run from the manager itself or a host in the same network that has a Cloudify CLI installed. 
These are the steps to run it:
1. Fill in the `aio_replace_certificates_config.yaml` file with the relevant information. Please follow the comments in the file. A few notes:
    * Either both certificate and key must be provided, or neither.
    * In order to replace a CA certificate, all related certificates need to be replaced as well. 
E.g. if you want to replace the Manager CA certificate, you will need to specify a new internal certificate for the manager and a new certificate for the RabbitMQ.
1. Run the script using the CLI environment: `/opt/cfy/embedded/bin/python main.py`.
1. Optional flags:
    * `--config-path` - The path to the `aio_replace_certificates_config.yaml`. The default path is 
    `./aio_replace_certificates_config.yaml`.
    * `-v, --verbose` - Log more information.


## Notes
1. The script uses `sudo` commands, therefore, sudo permissions for the ssh user are needed on each one of the hosts.
1. The script installs automatically the following on all hosts:
    * `epel-release`
    * `python-pip`
    * `ruamel.yaml==0.15.94` package
    * `requests>=2.24.0,<2.25` package
    * `retrying==1.3.3` package
1. In case you replaced the CA certificate on the managers, and you are using a CLI from a different host than a manager, 
you will need to change its (the CLI) CA certificate configuration. This can be done using the command
`cfy profiles set -c <new-ca-path>`.
1. In case of a failure, you can SSH into the failed host and find the log file under 
`/tmp/new_cloudify_certs/replace_certificates.log`. 
This log file always keeps logs of level DEBUG and above.
