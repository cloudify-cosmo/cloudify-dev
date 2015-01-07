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
git checkout build-<version>
git pull origin build-<version> (update the local branch if needed)
git merge master
git push origin build-<version>
```

**Note**

If the changes you make contain links to spec files,
make sure the you use the latest version when commiting to master, and the appropriate version for the build branch.

## Re-tag

**After updating build branch:**

```bash
git checkout build-<version>
git tag -f <version> (recreate tag locally from build branch)
git push origin :refs/tags/<version> (delete existing tag from remote)
git push origin <version> (push tag to remote)
```

