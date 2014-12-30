# Cloudify Release Flow

Sequence Diagram goes here..

## Builds

### Cloning Repositories

Before we create a build we clone all of Cloudify's repositories that are a part of the release.
This happens for Nightly, Release(GA/Milestone) and Patch releases.

### Setting Versions

Before creating the build, we need to set a branch for it.

* Nightly - master
* Release - X.Y(mZ)-build
* Patch - X.Y-patchZ

We set the SHA commit in environment variables and later use them in our Vagranfiles to create packages according to the tested commits.

We configure the manager blueprint files with the URL's of the packages that we will be creating.

We run the version-tool to change the versions in the different files.

We then commit all of the changes to the relevant branch.

### Tagging

From everything that we did up to here we create tags to enable unit and integration tests run in travis. This is only relevant to Nighlies and Releases, since in patches
we create our packages from the patch branches rather than tags.

### Unit and Integration Tests

Travis runs unit and integration tests on the newly created tags.
If the tests fail, the packages are created but the system tests won't run.

### Uploading YAML files

We upload the types.yaml file to S3.
We upload the plugin.yaml files from all plugins in the build to S3.

### Creating Artifacts

We then create the following:

#### Agents

We use our Vagrantfiles to load machines in Amazon. These machines are provisioned to create agent packages.
We use the cloudify-agent-packager to create the agent tar files.
We then copy the created tar file directly to S3 and Tarzan.

#### UI

To create the UI package from the cloudify-ui repository we run the build on the cloned repo and get a tar file.
We then copy the created tar file directly to S3 and Tarzan.

#### Dockerfiles

#### Docker Images

We use Vagrantfiles to create all of our Docker images. When the image creation process is complete, we move all of the tars to S3 and Tarzan.

#### Quickstart Vagrantbox

We use a Vagrantfile to provision the manager on a Vagrant machine in Amazon and the create a box from it. The box is then copied to S3 and Tarzan.
We provide a single Vagrantfile to be used in Quickstart that uses the created Vagrantbox.

## System Tests

We then run the system tests based on all of the creater artifacts.

## PyPI Modules

We currently manually run a pypi deploy after all systems tests have passed on a milestone/ga release.

## Documentation

FILL IN HERE
In addition, the version tool updates versions in the documentation to match the new release.

## ReadTheDocs

Several of our modules have readthedocs pages. We currently manually build them upon release.

## Alerting

Emails, Flowdock, etc...

Upon release we send an email with all packages for that release.


## Patches

