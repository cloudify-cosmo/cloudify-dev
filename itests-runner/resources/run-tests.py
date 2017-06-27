#!/usr/bin/env python

import argparse, datetime, os, fnmatch, json, sys


DEFAULT_PATTERN = 'test_*.py'
DEFAULT_WEIGHT = 100


def find_group_with_minimum_weight(group_weight):
    min_weight = min(group_weight)
    for i in range(len(group_weight)):
        if group_weight[i] == min_weight:
            return i
    raise RuntimeError()


def get_module_weight(weights, module_name):
    """Return the module weight for `module_name` as listed in the `weights` dict.
    If not found, return DEFAULT_WEIGHT.
    
    For example:
    module_name = "integration_tests/tests/agentless_tests/test_workflow.py"
    weights = {
        "agentless_tests/test_workflow.py": 123.51
    }

    The modules in the weight files contains a shorter path as they are extracted
    from the xunit report.
    """
    for key, value in weights.items():
        if module_name.endswith(key):
            return value
    else:
        return DEFAULT_WEIGHT

def split_modules_to_groups(test_modules, number_of_groups, weights):
    group_weight = [0 for _ in range(number_of_groups)]
    modules_per_group = [[] for _ in range(number_of_groups)]

    for module in test_modules:
        module_weight = get_module_weight(weights, module)
        group_index = find_group_with_minimum_weight(group_weight)
        group_weight[group_index] += module_weight
        modules_per_group[group_index].append(module)

    return modules_per_group, group_weight


def get_config(config_file):
    with open(config_file, 'r') as f:
        return json.loads(f.read())


def get_test_modules_for_path(tests_path, pattern, excluded_modules):
    test_modules = []
    for root, dirs, files in os.walk(tests_path):
        matching_files = [
            os.path.join(root, x) for x in fnmatch.filter(files, pattern)
        ]
        for exclude in excluded_modules:
            matching_files = [x for x in matching_files if exclude not in x]
        test_modules.extend(matching_files)
    return test_modules


def get_test_modules(config, pattern, repos_dir):
    tests_path = config['tests_path']
    excluded_modules = config['excluded_modules']
    test_modules = []
    for tp in tests_path:
        tp_modules = get_test_modules_for_path(os.path.join(repos_dir, tp), pattern, excluded_modules)
        print('# Found the following modules for {0}: {1}'.format(tp, json.dumps(tp_modules, indent=2)))
        test_modules.extend(tp_modules)
    return test_modules


def get_test_modules_weights(weights_file):
    weights = {}
    if weights_file:
        with open(weights_file, 'r') as f:
            weights = json.loads(f.read())
    return weights
    

def _run_modules_tests(test_modules, group_number, retry_on_failure=False):
    """Runs tests for the provided test_modules and returns a list of failed modules.

    test_modules is a tuple (index, test_module)
    """
    failed_modules = []
    for i, test_module in test_modules:
        command = 'nosetests -v -s --nologcapture --with-id --tests "{0}" --with-xunit --xunit-file $HOME/report-{1}-{2}.xml --xunit-testsuite-name "Server-{1}"'.format(
                test_module, group_number, i)
        exit_code = os.system(command)

        if exit_code != 0 and retry_on_failure:

            print('# Running failed tests again..')

            command = 'nosetests -v -s --nologcapture --failed --tests "{0}" --with-xunit --xunit-file $HOME/report-{1}-{2}.xml --xunit-testsuite-name "Server-{1}"'.format(
                    test_module, group_number, i)
            exit_code = os.system(command)

        if exit_code != 0:
            failed_modules((i, test_module))

    return failed_modules


def run_tests(repos_dir, group_number, number_of_groups, pattern, dry_run, weights_file, config, retry_on_failure=False):

    test_modules_weights = get_test_modules_weights(weights_file)

    print('# Collecting tests [group_number={0}, number_of_groups={1}, pattern={2}, dry_run={3}, weights_file={4}]'.format(
        group_number, number_of_groups, pattern, dry_run, weights_file))

    test_modules = get_test_modules(config, pattern, repos_dir)

    modules_per_group, groups_weight = split_modules_to_groups(test_modules, number_of_groups, test_modules_weights)

    print('# Groups weights: {0}'.format(json.dumps(groups_weight)))

    print('# Calculated groups:\n{0}'.format(json.dumps(modules_per_group, indent=2)))

    test_modules_to_run = modules_per_group[group_number - 1]

    print('# Running test modules in group number {0}'.format(group_number))

    if dry_run:
        os.system('nosetests -v --collect-only --tests {0}'.format(','.join(test_modules_to_run)))
        sys.exit(0)

    failed_modules = _run_modules_tests(enumerate(test_modules), group_number, retry_on_failure)

    print('# Failed modules: {0}'.format(json.dumps(failed_modules)))

    return 0 if len(failed_modules) == 0 else 1


def simulate(repos_dir, pattern, weights_file, config):
    test_modules_weights = get_test_modules_weights(weights_file)
    test_modules = get_test_modules(config, pattern, repos_dir)

    print('-' * 126)
    print('Servers   Time    Seconds   Per Server')
    print('-' * 126)

    for number_of_groups in range(10):
        modules_per_group, groups_weight = split_modules_to_groups(test_modules, number_of_groups + 1, test_modules_weights)
        max_time_in_seconds = max(groups_weight)
        max_time = str(datetime.timedelta(seconds=max_time_in_seconds)).split('.')[0]
        print(' {0:3}    {1}   {2:7.2f}   {3}'.format(number_of_groups + 1, max_time, max_time_in_seconds, ', '.join(['{0:8.2f}'.format(x) for x in groups_weight])))


def validate_args(args):
    if not args.simulate:
        if args.number_of_groups <= 0:
            print('number_of_groups should be > 0')
            sys.exit(1)
        if args.group_number > args.number_of_groups or args.group_number < 1:
            print('group_number should be between 1 to {0}'.format(args.number_of_groups))
            sys.exit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--repos', type=str, required=True,
                        help='Path where Cloudify repositories are checked out.')
    parser.add_argument('--group-number', type=int, required=False, default=-1,
                        help='Determines the group of tests to run (1-N).')
    parser.add_argument('--number-of-groups', type=int, required=False, default=-1,
                        help='Determines the number of groups the tests will be split to.')
    parser.add_argument('--pattern', type=str, required=False, default=DEFAULT_PATTERN,
                        help='Determines the number of groups the tests will be split to.')
    parser.add_argument('--dry-run', action='store_true',
                        help='If specified, tests will not actually run.')
    parser.add_argument('--weights-file', type=str, required=False,
                        help='A JSON file containing test modules weights used for optimization.')
    parser.add_argument('--simulate', action='store_true',
                        help='Simulate and estimate running times for different number of groups.')
    parser.add_argument('--config-file', type=str, required=True,
                        help='Config file path (config.json).')
    parser.add_argument('--retry-on-failure', action='store_true',
                        help='Retry module tests on failure (up to one module).')

    args = parser.parse_args()
    validate_args(args)

    config = get_config(args.config_file)

    if args.simulate:
        simulate(args.repos, args.pattern, args.weights_file, config)
    else:
        exit_code = run_tests(args.repos,
                              args.group_number,
                              args.number_of_groups,
                              args.pattern,
                              args.dry_run,
                              args.weights_file,
                              config,
                              args.retry_on_failure)
        sys.exit(exit_code)
