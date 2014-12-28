This document describes Cloudify's packages release process to PyPi
and information about how to add additional repositories to the process.

## Release flow

The process is based on Travis CI's [Deploy Mechanism](http://docs.travis-ci.com/user/deployment/).
This allows us to deploy packages to a public PyPi repository very easily.
The deployment only takes place if the unit tests passed successfully, and certain conditions were met.

![PyPi Flow](images/pypi_flow.png)

### Trigger

At the end of each milestone we trigger a deployment by creating a branch called `pypi-release`.
After the package is deployed successfully, we delete the branch.
We trigger with a branch and not a tag because currently Travis has a [known bug](https://github.com/travis-ci/travis-ci/issues/1675) which doesn't allow choosing a specific tag as a release trigger.

### Credentials

PyPi credentials are being encrypted inside `.travis.yml` using the [Travis Encryption Mechanism](http://docs.travis-ci.com/user/encryption-keys/).
Credentials are being encrypted with an asymmetric encryption, so each repository needs to encrypt/decrypt the keys separately, even if the credentials are the same.
You will need to use the [Travis command line](https://github.com/travis-ci/travis.rb) in order to encrypt your credentials.

### Post deploy

A post deploy script runs after a deployment was done (`travis-utils`) and verifies that the latest sdist is indeed the version that's currently located in PyPi.
This is done because Travis seem to ignore [Certain failures](https://github.com/travis-ci/travis-ci/issues/3058) during the deploy process to PyPi.

See the following reference `.travis.yml` which includes all of the flow steps described above:

```yaml
language: python
python:
  - ...
env:
  - ...
install:
  - ...
script:
  - ...
deploy:
  provider: pypi
  server: https://pypi.python.org/pypi
  on:
    branch: pypi-release
    condition: ...
  user:
    secure: ...
  password:
    secure: ...
after_deploy:
  - git clone https://github.com/cloudify-cosmo/travis-utils.git
  - python travis-utils/validate_pypi.py -v || exit 1
```

## Adding a new repository to the PyPi deploy process

### Register package on PyPi

Place your PyPi credentials in ~/.pypirc config:

```
[distutils]
index-servers =
    pypi
    pypitest

[pypi]
repository: https://pypi.python.org/pypi
username: {{your_username}}
password: {{your_password}}

[pypitest]
repository: https://testpypi.python.org/pypi
username: {{your_username}}
password: {{your_password}}
```
Now register your package:

* `python setup.py register -r pypitest` for test PyPi
* `python setup.py register -r pypi` for official PyPi


### Add `deploy` config section to `.travis.yml`

add the following to your `.travis.yml`:
```
deploy:
  provider: pypi
  server: https://pypi.python.org/pypi
  on:
    branch: pypi-release
    condition: ...
after_deploy:
  - git clone https://github.com/cloudify-cosmo/travis-utils.git
  - python travis-utils/validate_pypi.py -v || exit 1
```

Note that you might want to set the condition if running with a test matrix.
For example, if you have multiple TOX environments, you may want to set your condition to: `$TOX_ENV = py27` so that a deployment will only happen under the Python2.7 environment and not twice or more.

### Add encrypted credentials

Using Travis CLI run the following commands:
* `travis encrypt --add deploy.user` - to add username
* `travis encrypt --add deploy.password` - to add password

After this, you should see the user & password configurations as encrypted strings.

### Config QuickBuild

QuickBuild needs to be configured to run the automation part in the end of the milestone.
