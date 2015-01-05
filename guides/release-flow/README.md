# Cloudify Release Checklist

- Docker Image(s)
- Docker File(s)
- Agent Packages
    - Ubuntu Precise
    - Ubuntu Trusty
    - Centos Final
    - Windows
- UI
- VagrantBox
- All System Tests Passed
- Uploads
    - types.yaml
    - plugin.yamls
    -
- PyPI
    - REST Client
    - Plugins Common
    - DSL Parser
    - Script Plugin
    - Diamond Plugin
    - Agent Packager
- ReadTheDocs
    - REST Client
    - Plugins Common
    - CLI
- Documentation
    - Verify latest.
    - Verify website points to the new version
- Alert
    - Flowdock
    - Mail

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
We use the cloudify-agent-packager to create the agents' tar files.
We then copy the created tar files directly to S3 and Tarzan.

#### UI

To create the UI package from the cloudify-ui repository we run the build on the cloned repo and get a tar file.
We then copy the created tar file directly to S3 and Tarzan.

#### Dockerfiles

Need to decide

#### Docker Images

We use Vagrantfiles to create all of our Docker images. When the image creation process is complete, we move all of the tars to S3 and Tarzan.

#### Quickstart Vagrantbox

We use a Vagrantfile to provision the manager on a Vagrant machine in Amazon and the create a box from it. The box is then copied to S3 and Tarzan.
We provide a single Vagrantfile to be used in Quickstart that uses the created Vagrantbox.

## System Tests

We then run the system tests based on all of the creater artifacts.

## PyPI Modules

We currently manually run a PyPI deploy after all systems tests have passed on a milestone/ga release.

## Documentation

Currently, there's no possible flow to update the documentation. It is updated manually and pushed. Once we move to a version-controlled documentation system, we'll be able to automatically build the specific version meant for release.
In addition, the version tool updates versions in the documentation to match the new release.

## ReadTheDocs

Several of our modules have readthedocs pages. We currently manually build them upon release.

## Alerting

Emails, Flowdock, etc...

Upon release we send an email with all packages for that release.


# Patch Releases

- is the patch limited to single component or multiple component?
    - if single component, release only the component (cloud plugin, for instance)
    - if more then one, build and release everything
    - Decision has to be per-case.
- A patch is not per customer - may be used for multiple cases.
- Patch should have a feature flag to enable/disable the functionality, if relevant/possible.
- patches are for short term use. Next GA release should solve the problem in a standard way.
- feature patches should be documented to indicate this branch updates a certain feature.
- Patches will not be available in pypi. This fact must appear clearly in the patch release.
- The patch release should include the list of built packages. It should also include links to github repos/branches if required.

- patch should have a version/patch number. It should be in the version file of the modified packages. This needs a JIRA.
- each built package should have meta-data indicating version/patch.
- version should not change for each patch. This will break dependencies. Other users will also install if they see it.
- patch number should be available in CLI and UI. This needs a JIRA
- test-drive the patch testing policy. This should be tested soon.
- the build should specify which branches to use, per repo.
    - build should have a 'default' branch. It should be possible to enter a separate branch for particular repos.

- Relating to the 3.1 GA sprint, the Early Access build was marked b85 all through the GA release. Build number must move forward.

- plugin version dependencies - use >= or == for version numbers? This is an open issue