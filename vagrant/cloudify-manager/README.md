Cloudify Vagrant Manager
========================

When developing features that should be cloud agnostic, it can be very useful to use vagrant to spin up VM's. This way you don't have to worry about credentials and sporadic network issues.
Plus, the configuration is much simpler and the launch time is significantly faster.
This Vagrantfile allows you to have a fully functioning manager with just one command line. It contains 3 VM definitions.
<br>
<br>
All VM's use the [Simple Manager Blueprint](https://github.com/cloudify-cosmo/cloudify-manager-blueprints/tree/master/simple) to simply (get it?) bootstrap cloudify on an existing machine.

## The *prod_docker* VM


All this VM does is bootstrap the manager using the the cloudify docker container. You cannot change neither the code nor the packages running on the manager. To start it just run:

```bash
vagrant up prod_docker
```

or, since this is the default machine:

```bash
vagrant up
```

**Note**

There is currently an issue which prevents this process from being completely automated. To read more you can have a look at [JIRA](https://cloudifysource.atlassian.net/browse/CFY-1910).
For now, if you see this error you need to run the following commands:

```bash
vagrant ssh prod_docker
sudo docker rm cfy
sudo docker run -t --volumes-from data -p 80:80 -p 5555:5555 -p 5672:5672 -p 53229:53229 -p 8100:8100 -p 9200:9200 -e MANAGEMENT_IP=172.28.128.4 --restart=always --name=cfy -d cloudify /sbin/my_init
```


## The *prod-packages* VM

All this VM does is bootstrap the manager using the deb packages. You cannot change neither the code nor the packages running on the manager. To start it just run:

```bash
vagrant up prod-packages
```

## The *dev-packages* VM

This VM does exactly what the *prod-packages* VM does, but it also executes the *setup-dev-env* task on the newly started manager.
You can read about this task [Here](https://github.com/cloudify-cosmo/cloudify-dev/blob/master/tasks), but basically, it allows you to easily make changes to your code and apply them to the manager. To start the VM just run:

```bash
vagrant up dev-packages
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

There are some useful environment variables you can use:

- MANAGER_BLUEPRINTS_BRANCH - The manager blueprint branch you want to use to bootstrap with.
- CLOUDIFY_SOURCE_FOLDER - Path to a folder on your host that contains the cloudify source code projects.
- CLI_BRANCH - The cli branch used to bootstrap. The default value will be the value set for MANAGER_BLUEPRINTS_BRANCH.
- USE_TARZAN - Set this variable to any string to use local tarzan URL's instead of amazon s3 buckets.
