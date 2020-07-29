# Replace Certificates script
The replace-certificates script enables users of Cloudify cluster v5.0.5 to replace certificates on all cluster instances. Important note:
    * The script doesn't take care of replacing certificates on agents.
    * Since this script is dedicated for Cloudify v5.0.5 users, it uses Python2.
    * Please keep all the script's files in the same directory. 

## Usage
The script `main.py` can run from on of the managers in the cluster or a different host in the same network as the cluster.  
These are the steps in order to run it: 
1. Install all packages specified in `client_requirements.txt`.
1. Fill in the `replace_certificates_config.yaml` file with the relevant information.
For each host you would need to specify its host ip new certificates' paths. Few notes:
    * For each instance, either both certificate and key must be provided, or neither.
    * In order to replace a CA certificate, all related instances' certificates need to be replaced as well. 
E.g. if you want to replace the RabbitMQ CA certificate, you will need to specify new certificates for all RabbitMQ instances.
    * **Special case:** In case  of replacing the "postgresql_server" CA cert, the "manager" instances' 
postgresql_client certificates need to be replaced as well.
1. Optional flags:
    * `--config-path` - The path to the `replace_certificates_config.yaml`. The default path is 
    `./replace_certificates_config.yaml`.
    * `-v, --verbose` - Log more information.

## Notes
1. The script uses `sudo` commands, therefore, root access is needed in each one of the instances.
1. The script installs on all cluster instances the following:
    * `epel-release`
    * `python-pip`
    * `ruamel.yaml==0.15.94` package
    * `requests==2.7.0` package
    * `retrying==1.3.3` package
1. In case you replaced the CA certificate on the managers, and you are using a CLI from a different host than one of the managers, 
you will need to change its (the CLI) CA certificate configuration. This can be done with rhe command
`cfy profiles set -c <new-ca-path>`
1. In case of a failure, you can SSH into the failed instance and find the log file under 
`/tmp/new_cloudify_certs/replace_certificates.log`. 
This log file always keeps logs of level DEBUG and above.
