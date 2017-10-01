import os

from time import time
from threading import Thread
from collections import OrderedDict

import sh
import argh
import git
from colorama import Fore
from argh import arg


CORE_REPOS = [
    'cloudify-dsl-parser',
    'cloudify-rest-client',
    'cloudify-plugins-common',
    'cloudify-diamond-plugin',
    'cloudify-agent',
    'cloudify-cli',
    'cloudify-manager',
    'cloudify-manager-blueprints',
    'cloudify-premium',
    'cloudify-script-plugin',
    'cloudify-amqp-influxdb',
    'docl'
]
DEV_REPOS = [
    'cloudify-fabric-plugin',
    'cloudify-system-tests',
    'cloudify-dev'
]
REPOS = CORE_REPOS + DEV_REPOS


MASTER = 'master'
REPO_BASE = os.environ.get('CLAP_REPO_BASE',
                           os.path.expanduser('~/dev/repos/'))
BASE_SSH_GITHUB_URL = 'git@github.com:cloudify-cosmo/{0}.git'
BASE_HTTPS_GITHUB_URL = 'https://github.com/cloudify-cosmo/{0}.git'

command = argh.EntryPoint(
    'clap',
    dict(description='Custom commands that run on several cloudify repos')
)


def get_repo_path(repo):
    return os.path.join(REPO_BASE, repo)


def create_repo_base():
    if not os.path.exists(REPO_BASE):
        print logger.yellow('Creating base repos dir: {0}'.format(REPO_BASE))
        os.makedirs(REPO_BASE)


def run_multi_threaded(threads):
    for t in threads:
        t.daemon = True
        t.start()

    for t in threads:
        t.join()


class Logger(object):
    @staticmethod
    def red(msg):
        return Fore.RED + msg + Fore.RESET

    @staticmethod
    def yellow(msg):
        return Fore.YELLOW + msg + Fore.RESET

    @staticmethod
    def green(msg):
        return Fore.GREEN + msg + Fore.RESET

    @staticmethod
    def blue(msg):
        return Fore.BLUE + msg + Fore.RESET

    def error(self, msg, should_exit=True):
        print self.red(msg)
        if should_exit:
            exit(1)

    @staticmethod
    def log(repo, line):
        repo = Fore.GREEN + repo
        print '{0:<35}| {1}{2}'.format(repo, line, Fore.RESET)

    def header(self, header):
        header = self.blue(header)
        print '{s:{c}^{n}}'.format(s=header, n=40, c='-')

    def log_multiline(self, repo, output):
        for line in output.split('\n'):
            if line:
                line = Fore.YELLOW + line
                self.log(repo, line)

    def log_status(self, line, repo):
        if not line:
            return

        if len(line.split()) == 2:
            status_out, line = line.split()
            status_out = Fore.RED + status_out
            line = Fore.GREEN + line
            line = '{0} {1}'.format(status_out, line)
        else:
            line = Fore.GREEN + line

        self.log(repo, line)

    def log_install(self, line, name, verbose):
        if not line:
            return

        if verbose or line.startswith('Successfully installed'):
            line = Fore.YELLOW + line
            self.log(name, line)


logger = Logger()


class Git(object):
    def __init__(self, repo=None):
        self._git = git.Git(get_repo_path(repo))
        self._repo = repo

    def validate_repo(self, repo=None):
        repo = repo or self._repo
        repo_path = get_repo_path(repo)
        if not os.path.exists(repo_path):
            msg = 'Folder `{0}` does not exist'.format(repo_path)
            return logger.red(msg)

        try:
            self._git.status()
        except sh.ErrorReturnCode, e:
            if 'Not a git repository' in str(e):
                msg = '`{0}` is not a git repository'.format(repo_path)
            else:
                msg = str(e)
            return logger.red(msg)

        return None

    def status(self):
        return self._git.status('-s').strip()

    def get_current_branch_or_tag(self, hide_tags=False):
        """
        Get the value of HEAD, if it's not detached, or emit the
        tag name, if it's an exact match. Throw an error otherwise
        """
        branch = self._git.rev_parse('--abbrev-ref', 'HEAD').strip()
        if hide_tags:
            return branch

        tags = self._git.tag('--points-at', 'HEAD').split()
        result = branch if branch != 'HEAD' else ''

        if tags:
            tags = ', '.join(tags)
            tags = logger.yellow('[{0}]'.format(tags))
            result = '{0} {1}'.format(result, tags).strip()
        return result

    def pull(self):
        return self._git.pull()

    def checkout(self, branch, new=False):
        checkout_args = [branch]
        if new:
            logger.log(self._repo, 'Creating a branch named {0}'.format(branch))
            checkout_args = ['-b'] + checkout_args

        return self._git.checkout(*checkout_args)

    def _git_clone(self, repo, branch, shallow, ssh):
        base_url = BASE_SSH_GITHUB_URL if ssh else BASE_HTTPS_GITHUB_URL
        full_url = base_url.format(repo)
        args = [full_url, get_repo_path(repo), '--branch', branch]
        if shallow:
            args += ['--depth', 1]
        self._git.clone(*args)

    def clone_repo(self, repo, repo_branch, shallow, ssh):
        if not self.validate_repo(repo):
            return logger.yellow('Folder already exists. '
                                 'Repo probably already cloned')
        else:
            self._git.clone(repo, repo_branch, shallow, ssh)
            return logger.green('Successfully cloned `{0}`'.format(repo))


class Repos(object):
    def __init__(self, branch=MASTER, dev=True, requirements=None):
        self._branch = branch
        self._full_repos_list = REPOS if dev else CORE_REPOS
        if requirements:
            self._repos = self._parse_requirements(requirements)
        else:
            self._repos = OrderedDict((repo, branch)
                                      for repo in self._full_repos_list)

    def __iter__(self):
        return iter(self._repos.items())

    @property
    def repos(self):
        return iter(self._repos.items())

    def _parse_requirements(self, requirements):
        repos_dict = {}
        with open(requirements, 'r') as f:
            for line in f.readlines():
                line = line.strip()
                if '@' in line:
                    repo, repo_branch = line.split('@')
                else:
                    repo, repo_branch = line, self._branch
                repos_dict[repo] = repo_branch

        result_dict = OrderedDict()
        # This extra loop makes sure the order of the repos in the dict is
        # correct
        for repo in self._full_repos_list:
            if repo in repos_dict:
                result_dict[repo] = repos_dict[repo]

        return result_dict

    @property
    def cloudify_packages(self):
        packages = OrderedDict()
        for repo, _ in self.repos:
            packages[repo] = repo

        manager_repo = packages.pop('cloudify-manager', None)
        packages.pop('cloudify-manager-blueprints', None)
        packages.pop('cloudify-dev', None)

        if manager_repo:
            packages['cloudify-rest-service'] = 'cloudify-manager/rest-service'
            packages['cloudify-integration-tests'] = 'cloudify-manager/tests'
            packages['cloudify-system-workflows'] = 'cloudify-manager/workflows'  # NOQA
            packages['cloudify-cloudify-riemann-controller-plugin'] = \
                'cloudify-manager/plugins/riemann-controller'
        return packages.iteritems()


repos = Repos()


@command
def status(hide_tags=False):
    logger.header('Status')
    for repo, _ in repos.repos:
        git = Git(repo)
        output = git.validate_repo()
        if output:
            logger.log(repo, output)
            continue

        branch = git.get_current_branch_or_tag(hide_tags=hide_tags)
        logger.log(repo, branch)

        for line in git.status().split('\n'):
            logger.log_status(line, repo)


@command
def pull():
    def _pull_repo(repo):
        git = Git(repo)
        try:
            output = git.pull()
        except sh.ErrorReturnCode:
            output = 'No upstream defined. Skipping pull.'
        logger.log_multiline(repo, output)

    logger.header('Pull')
    threads = [Thread(target=_pull_repo, args=(repo, ))
               for repo, _ in repos.repos]
    run_multi_threaded(threads)


@command
def install(verbose=False):
    logger.header('Install')
    pip = sh.pip.bake()

    for repo, path in repos.cloudify_packages:
        repo_path = get_repo_path(path)
        if not os.path.exists(repo_path):
            msg = logger.red('Folder `{0}` does not exist'.format(repo_path))
            logger.log(repo, msg)
            continue

        try:
            output = pip.install('-e', repo_path)
        except Exception, e:
            error = Fore.RED + 'Could not pip install repo: {0}'.format(e)
            logger.log(repo, error)
            continue

        for line in output.split('\n'):
            logger.log_install(line, repo, verbose)


@command
def checkout(branch, hide_tags=False):
    global repos
    repos = Repos(branch)

    logger.header('Checkout')
    for repo, repo_branch in repos.repos:
        git = Git(repo)
        try:
            git.checkout(repo_branch)
            branch = git.get_current_branch_or_tag(hide_tags=hide_tags)
            logger.log(repo, branch)
        except sh.ErrorReturnCode:
            output = 'Could not checkout branch `{0}`'.format(repo_branch)
            logger.log_multiline(repo, output)


@command
@arg('modified',
     help='Using AUTO will scan all of the repos for changes. If a repo was '
          'modified a new branch would be automatically created. '
          '(so you at your own risk)')
@arg('branch_name', help='The new branch name')
def new_task(branch_name, modified):
    """
    Checkout a new branch
    """
    global repos
    repos = Repos(branch_name)

    logger.header('Creating new local branches')
    if modified == 'AUTO':
        # checkout new branches in every modified repo
        for repo, _ in repos:
            git = Git(repo)
            status = git.status().strip().split()
            if modified and status and 'M' in status[0]:
                # This branch was indeed modified
                git.checkout(branch_name, new=True)
    else:
        for repo in modified.split(';'):
            if not repo.startswith('cloudify'):
                repo = 'cloudify-{0}'.format(repo)
            git = Git(repo)
            git.checkout(branch_name, new=True)

@command
def clone(shallow=False, ssh=True):
    logger.header('Clone')
    create_repo_base()
    git = Git()

    def _clone_repo(repo, repo_branch, shallow):
        try:
            output = git.clone_repo(repo, repo_branch, shallow, ssh)
        except sh.ErrorReturnCode, e:
            error = str(e)

            if 'fatal: destination path' in error:
                error = 'Repo is probably already cloned (the folder exists)'
            if 'fatal: Could not read from remote repository' in error:
                error = 'Make sure you have your GitHub SSH key set up'

            output = 'Could not clone repo `{0}`: {1}'.format(repo, error)
            output = logger.red(output)

        logger.log_multiline(repo, output)

    threads = [
        Thread(target=_clone_repo, args=(repo, repo_branch, shallow))
        for repo, repo_branch in repos.repos
    ]
    run_multi_threaded(threads)


@command
def setup(branch=MASTER, requirements=None, dev=False):
    # Overriding the default repos object, to reflect the
    # branch/requirements file
    global repos
    repos = Repos(branch=branch, requirements=requirements, dev=dev)

    clone(shallow=True, ssh=False)
    status()
    install()


def main():
    start_time = time()
    command()
    end_time = time()
    logger.header('Took {:.2f} seconds'.format(end_time - start_time))
