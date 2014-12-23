Cloudify Vagrant Manager
========================

When developing features that should be cloud agnostic, it can be very useful to use vagrant to spin up VM's. This way you don't have to worry about credentials and sporadic network issues.
Plus, the configuration is much simpler and the launch time is significantly faster.
This Vagrantfile allows you to have a fully functioning manager with just one command line. It contains two VM definitions.
<br>
<br>
Both VM's use the [Simple Manager Blueprint](https://github.com/cloudify-cosmo/cloudify-manager-blueprints/tree/master/simple) to simply (get it?) bootstrap cloudify on an existing machine.
In our case, this machine is an *ubuntu precise64* provisioned by vagrant, using the virtualbox provider.

## The *prod* VM

All this VM does is bootstrap the manager. You cannot change neither the code nor the packages running on the manager. To start it just run:

```bash
vagrant up prod
```

## The *dev* VM

This VM does exactly what the *prod* VM does, but it also executes the *setup-dev-env* task on the newly started manager.
You can read about this task [Here](https://github.com/cloudify-cosmo/cloudify-dev/blob/master/tasks), but basically, it allows you to easily make changes to your code and apply them to the manager. To start the VM just run:

```bash
vagrant up dev
```

Now comes the nifty part. After you make changes to your code, **ssh into the vm by running `vagrant ssh dev`**.
You will automatically be placed inside a directory where you can use the `cfy` command.
If the changes you made do not affect the agent package, just run:

```bash
cfy dev --tasks-file /home/vagrant/cloudify/cloudify-dev/tasks/tasks.py --task restart-services
```

Otherwise, run:

```bash
cfy dev --tasks-file /home/vagrant/cloudify/cloudify-dev/tasks/tasks.py --task update-agent-package
cfy dev --tasks-file /home/vagrant/cloudify/cloudify-dev/tasks/tasks.py --task restart-services
```

**Note**

Before you run the vagrant commands, some environment variables need to be set.

- MANAGER_BLUEPRINTS_BRANCH - The manager blueprint branch you want to use to bootstrap with.
- CLOUDIFY_SOURCE_FOLDER - Path to a folder on your host that contains the cloudify source code projects.

Vagrant will fail with an appropriate error message if any of these are not set.