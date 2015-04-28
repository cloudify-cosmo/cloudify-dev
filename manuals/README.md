This document should contain manuals to common procedures.

# Re-taging and updating build branch

All cloudify repositories have tags corresponding to a particular version.
They also have a build-<version> branch, which the tag was created from at release time.
These tags are created automatically, However,
sometimes a need arises to re-tag a repository after the version was already released.
To do so, follow the following instructions:

## Update build-<version> branch

**After pushing changes to master:**

```bash
git checkout <version>-build
git pull origin <version>-build (update the local branch if needed)
git cherry-pick <commit1> <commit2> ...
git push origin <version>-build
```

**Note**

If the changes you make contain links to spec files,
make sure the you use the latest version when commiting to master, and the appropriate version for the build branch.

## Re-tag

**After updating build branch:**

```bash
git checkout <version>-build
git tag -f <version> (recreate tag locally from build branch)
git push origin :refs/tags/<version> (delete existing tag from remote)
git push origin <version> (push tag to remote)
```

# Cleaning up an openstack tenant (USE WITH CAUTION)

Sometimes during development you may find yourself in a situation where you
need to manually delete resources from you openstack environment. Most often
 than not, you will want to completely cleanup all resources, this can be
 easily done with the help of [ospurge](https://github.com/stackforge/ospurge) - An official stackforge project
 that does exactly that.

### A few notes:

- **Use this if and only if you have your OWN dedicated tenant on an
 openstack environment, as it will completely wipe out that tenant**
- **Contradicting a bit what is stated above, it will not delete key-pairs,
so be sure to delete them manually (locally as well - if needed)**

first install the ospurge client:

```bash
$ pip install ospurge
```

export the necessary environment variables:

```bash
$ export OS_USERNAME=admin
$ export OS_PASSWORD=password
$ export OS_TENANT_NAME=admin
$ export OS_AUTH_URL=http://localhost:5000/v2.0
```

first lets have a dry run to see what resources we are going to be deleting:

```bash
ospurge --dry-run --own-project
```

if the result is what you expected, lets go ahead and delete the resources.
note the `--dont-delete-project` flag which tells the client not to try and
delete the tenant, but just the resources.

```bash
ospurge --dont-delete-project --own-project --verbose
```

You can read more about this project at the [ospurge](https://github.com/stackforge/ospurge) page.
