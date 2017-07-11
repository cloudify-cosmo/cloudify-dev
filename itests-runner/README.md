
Cloudify Integration Tests Runner
=================================

Using this framework it is possible to run Cloudify's integration tests on an OpenStack environment.

## Installation

### Prerequisites

* Python 2.7.X + virtualenv.
* Terraform.
* git.
* OpenStack environment.


### Install Local Dependencies

* Checkout the `cloudify-dev` repository.
* Within a Python virtualenv run:

```bash
cd itests-runner
pip install -r requirements.txt
```

### Install Terraform

Download terraform from [here](https://www.terraform.io/downloads.html), and follow the installation instructions [here](https://www.terraform.io/intro/getting-started/install.html).


## The itest.py Program

```bash
$ ./itests.py -h
usage: itests.py [-h] {run,simulate,create-server} ...

positional arguments:
  {run,simulate,create-server}
    run                 Run integration tests
    simulate            Simulate servers distribution.
    create-server       Creates a test server.

optional arguments:
  -h, --help            show this help message and exit
```

## Running Tests

```bash
$ ./itests.py run -h
usage: itests.py run [-h] -n NUMBER_OF_SERVERS [-p PATTERN] [-k]

optional arguments:
  -h, --help            show this help message and exit
  -n NUMBER_OF_SERVERS, --number-of-servers NUMBER_OF_SERVERS
                        The number of servers to create and distribute the
                        tests to.
  -p PATTERN, --pattern PATTERN
                        Test modules pattern to match (default=test_*.py).
  -k, --keep-servers    Keep test servers up (test servers are terminated by
                        default).
```

Before running a test, make sure to source your OpenStack openrc file.
The openrc file contains the authentication details for your OpenStack account.
Information about downloading it from an OpenStack environment can be found [here](https://docs.openstack.org/user-guide/common/cli-set-environment-variables-using-openstack-rc.html).

Make sure your openrc file is set to use the OpenStack v2 API in both `OS_AUTH_URL` and `OS_IDENTITY_API_VERSION` environment variables.

OpenStack openrc file example (my-openrc.sh):
```bash
#!/bin/bash

export OS_AUTH_URL=https://rackspace-api.gigaspaces.com:5000/v2.0
export OS_TENANT_NAME="idan-tenant"
export OS_PROJECT_NAME="idan-tenant"
export OS_USERNAME="idan"
export OS_PASSWORD="GUESS-ME"
export OS_REGION_NAME="RegionOne"
export OS_IDENTITY_API_VERSION=2
```

Source the openrc file:
```bash
source my-openrc.sh
```

Running tests example:
```bash
./itests.py -n 1 --pattern "test_workflow.py"

...

Processing 1 report files..
-------------------------------------------
Module                                 Time
-------------------------------------------
agentless_tests/test_workflow.py    239.654

Test Report:
----------------------------------------------------------
Suite           Tests Errors Failures Skipped         Time
----------------------------------------------------------
TestSuite-1        20      0        0       0      239.654
----------------------------------------------------------
                   20      0        0       0      239.654

Creating work/report.html..
Done!

Execution time: 679.75 seconds.
```

The runner creates a `work` directory where terraform context and test reports will be stored in.

By the default, the runner will destroy the cloud resources it creates for running the tests.


### Tests Report

The framework generates an HTML file containing an aggregation of all xunit test reports found in the `work` directory.

In order to view the report, open the `work/report.html` file using your favourite browser.


## Simulate

In order to decide how many servers to use for running the tests, it is possible to simulate and estimate how long it will take to run the tests per `number of servers`.

```bash
$ ./itests.py simulate --help
usage: itests.py simulate [-h] --repos REPOS [-p PATTERN]

optional arguments:
  -h, --help            show this help message and exit
  --repos REPOS         The directory Cloudify repositories are checked-out
                        in.
  -p PATTERN, --pattern PATTERN
                        Test modules pattern to match (default=test_*.py).
```

Run:
```bash
$ ./itests.py simulate --repos ~/dev/repos

...

------------------------------------------------------------------------------------------------------------------------------
Servers   Time    Seconds   Per Server
------------------------------------------------------------------------------------------------------------------------------
   1    1:32:51   5571.96    5571.96
   2    0:47:16   2836.91    2836.91,  2735.05
   3    0:33:28   2008.65    1786.26,  1777.04,  2008.65
   4    0:26:50   1610.83    1254.05,  1366.25,  1610.83,  1340.83
   5    0:23:33   1413.67    1084.99,  1114.52,  1413.67,   910.60,  1048.18
   6    0:21:01   1261.04     726.85,   890.04,  1261.04,   927.27,  1055.83,   710.93
   7    0:19:00   1140.57    1140.57,  1019.31,   670.06,   829.01,   770.53,   566.77,   575.71
   8    0:18:25   1105.55     728.89,   482.58,   695.44,   475.00,   586.44,   998.24,   499.82,  1105.55
   9    0:17:01   1021.35     448.47,   534.03,   972.52,   411.68,   418.29,   635.04,   464.85,  1021.35,   665.72
  10    0:16:15    975.78     601.09,   387.26,   975.78,   379.33,   635.38,   379.51,   371.87,   946.80,   478.01,   416.93

Execution time: 0.02 seconds.
```

Please note that the time listed in the output does not include the time for creating the environment for running the tests, which is approximately 250-400 seconds.



## Create a Test Server

In order to create a test server with all dependencies for running tests manually run:
```bash
./itests.py create-server

...

Test server is up!
SSH to it by running: ssh -i /home/idanmo/dev/repos/integration-tests/work/ssh_key.pem centos@10.239.1.32
Or ./itests.py ssh

Execution time: 261.71 seconds.
```


## Connecting to Test Servers via SSH

In order to connect to a server (when it is up :-)) using SSH run:

```bash
./itests.py ssh <server-index>
```

`server-index` is 0 by default.


## Cleaning Up Cloud Resources

If from some reason the environment was not destroyed, use the provided `destroy.sh` script to destroy the envrionment:

```bash
./itests.py destroy
```

Please note that the script also deletes the `work` directory.



## Advanced Configuration

The advanced configuration file is located in `resources/config.json`.

By editing it, it is possible to change the following parameters:

* Branch name per repository.
* Paths to scan for tests.
* Test modules to exclude.
* Test server parameters.

For example:

```json
{
    "repositories": {
        "cloudify-dsl-parser": "master",
        "cloudify-rest-client": "master",
        "cloudify-plugins-common": "master",
        "cloudify-diamond-plugin": "master",
        "cloudify-script-plugin": "master",
        "cloudify-agent": "master",
        "cloudify-cli": "master",
        "cloudify-manager": "master",
        "cloudify-manager-blueprints": "master",
        "cloudify-amqp-influxdb": "master",
        "cloudify-premium": "master",
        "docl": "master"
    },
    "tests_path": [
        "cloudify-manager/tests/integration_tests/tests/agent_tests",
        "cloudify-manager/tests/integration_tests/tests/agentless_tests",
        "cloudify-premium/tests/integration_tests/multi_tenancy",
        "cloudify-premium/tests/integration_tests/security"
    ],
    "excluded_modules": [
        "test_n_instances.py",
        "policies",
        "test_hello_world.py",
        "ldap",
        "deployment_update"
    ],
    "test_server": {
        "image": "integration-tests-image",
        "flavor": "m1.medium"
    }
}
```


## Implementation

The framework is implemented using a bunch of Python and Bash scripts executed locally and remotely using `Terraform`.

Flow:
* Create the necessary cloud resources using `Terraform`.
* Setup the VMs with all necessary system and Cloudify dependencies.
* Split test modules (*.py files) to buckets (bucket per server) using weights from the `resources/weights.json` file using a greedy algorithm.
* Assign each test server with a test modules bucket.
* Run the tests.
* Collect xunit reports from all test servers and generate an HTML report.

The framework is designed to work with vanilla CentOS 7.X images.

Using a baked image with as many dependencies as possible is advised as it shortens the VM setup time tremendously.
