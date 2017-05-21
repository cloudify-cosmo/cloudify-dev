#!/usr/bin/env python

import argparse
import datetime
import glob
import json
import re
import os
from xml.etree import ElementTree

import colorama
import jinja2


class TestSuite(object):

    def __init__(self):
        self.name = None
        self.tests = 0
        self.errors = 0
        self.failures = 0
        self.skipped = 0
        self.testcases = []
        self.time = 0

    @property
    def test_classes(self):
        classes = set()
        for t in self.testcases:
            classes.add(t.classname)
        return list(classes)


class TestCase(object):

    def __init__(self):
        self.name = None
        self.classname = None
        self.passed = None
        self.error = None
        self.stdout = None
        self.stderr = None
        self.time = None


def build_test_case(testcase):
    case = TestCase()
    case.name = testcase.attrib['name']
    case.classname = testcase.attrib['classname']
    case.time = float(testcase.attrib['time'])
    case.passed = True
    for elem in testcase:
        if elem.tag == 'error':
            case.passed = False
            case.error = elem.text
        if elem.tag == 'failure':
            case.passed = False
        if elem.tag == 'system-out':
            case.stdout = elem.text
        if elem.tag == 'system-err':
            case.stderr = elem.text
    return case


def build_test_suite(testsuite):
    suite = TestSuite()
    suite.name = testsuite.attrib['name']
    suite.tests = int(testsuite.attrib['tests'])
    suite.errors = int(testsuite.attrib['errors'])
    suite.failures = int(testsuite.attrib['failures'])
    suite.skipped = int(testsuite.attrib['skip'])
    for testcase in testsuite:
        suite.testcases.append(build_test_case(testcase))
    suite.time = sum([x.time for x in suite.testcases])
    return suite


def merge_test_suites(testsuites):
    new_suites = []
    for server_suites in testsuites.values():
        new_suite = TestSuite()
        for suite in server_suites:
            new_suite.name = suite.name
            new_suite.errors += suite.errors
            new_suite.failures += suite.failures
            new_suite.tests += suite.tests
            new_suite.skipped += suite.skipped
            new_suite.time += suite.time
            new_suite.testcases.extend(suite.testcases)
        new_suites.append(new_suite)
    return new_suites


def seconds_to_timestamp(seconds):
    hms = str(datetime.timedelta(seconds=seconds)).split('.')[0].split(':')
    return '{0:0>2}:{1:0>2}:{2:0>2}'.format(hms[0], hms[1], hms[2])


def print_summary(testsuites):
    summary = TestSuite()
    fmt = '{0:15} {1:5} {2:6} {3:8} {4:7} {5}'
    print('')
    print('Test Report:')
    print('----------------------------------------------------------')
    print(fmt.format('Suite', 'Tests', 'Errors', 'Failures', 'Skipped', '        Time'))
    print('----------------------------------------------------------')
    for suite in sorted(testsuites, key=lambda x: x.name):
        summary.errors += suite.errors
        summary.failures += suite.failures
        summary.skipped += suite.skipped
        summary.tests += suite.tests
        summary.time += suite.time
        print(fmt.format(suite.name, suite.tests, suite.errors, suite.failures, suite.skipped, seconds_to_timestamp(suite.time).rjust(12)))
    print('----------------------------------------------------------')
    max_time = max([x.time for x in testsuites])
    print(fmt.format('', summary.tests, summary.errors, summary.failures, summary.skipped, seconds_to_timestamp(max_time).rjust(12)))
    colorama.init()
    print('')
    if summary.errors == 0 and summary.failures == 0 and summary.skipped == 0:
        print(colorama.Fore.LIGHTGREEN_EX + 'PASSED!' + colorama.Fore.RESET)
    else:
        print(colorama.Fore.LIGHTRED_EX + 'FAILED!' + colorama.Fore.RESET)
    print('')
    return summary


def extract_module_name(classname):
    return '/'.join(classname.split('.')[:-1]) + '.py'


def print_time_per_test_module(testsuites, work_dir):
    suites = []
    for server_suites in testsuites.values():
        suites.extend(server_suites)
    
    test_modules_time = {}

    for suite in suites:
        for case in suite.testcases:
            module_name = extract_module_name(case.classname)

            if module_name not in test_modules_time:
                test_modules_time[module_name] = {
                    'time': 0,
                    'classes': {}
                }
            test_modules_time[module_name]['time'] += case.time
            if case.classname not in test_modules_time[module_name]['classes']:
                test_modules_time[module_name]['classes'][case.classname] = case.time
            else:
                test_modules_time[module_name]['classes'][case.classname] += case.time

    max_module_name_length = max([len(x) for x in test_modules_time.keys()])

    print('-' * (max_module_name_length + 11))
    print('{0}       Time'.format('Module'.ljust(max_module_name_length)))
    print('-' * (max_module_name_length + 11))
    modules_list = [(k, v['time']) for k, v in test_modules_time.items()]
    for (class_name, t) in sorted(modules_list, key=lambda x: x[1]):
        print('{0} {1:10}'.format(class_name.ljust(max_module_name_length), seconds_to_timestamp(t).rjust(10)))
        if len(test_modules_time[class_name]['classes']) > 1:
            for cls_name, time in test_modules_time[class_name]['classes'].items():
                print(' * {0}: {1}'.format(cls_name.split('.')[-1], seconds_to_timestamp(time)))

    test_modules_time = {k: v['time'] for k, v in test_modules_time.items()}

    with open('{0}/weights.json'.format(work_dir), 'w') as f:
        f.write(json.dumps(test_modules_time, indent=2))
   

def create_html_report(work_dir):

    xml_files = glob.glob('{0}/*.xml'.format(work_dir))
    print('Processing {0} report files..'.format(len(xml_files)))

    testsuites = {}
    testsuites_list = []

    for xml_file in xml_files:

        tree = ElementTree.parse(xml_file)
        suite = build_test_suite(tree.getroot())

        if suite.name not in testsuites:
            testsuites[suite.name] = []
        testsuites[suite.name].append(suite)

    if not xml_files:
        print('No xunit test reports found.')
        return

    print_time_per_test_module(testsuites, work_dir)

    testsuites = merge_test_suites(testsuites)

    summary = print_summary(testsuites)

    with open('report.jinja2.html', 'r') as f:
        report_template = f.read()
                                        
    rendered_template = jinja2.Template(report_template).render({
        'testsuites': testsuites,
        'summary': summary
    })

    print('Creating {0}/report.html..'.format(work_dir))
    with open('{0}/report.html'.format(work_dir), 'w') as f:
        f.write(rendered_template)

    print('Done!')
    


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--work-dir', default='work', required=False,
                        help='Working directory to load xunit reports from.')
    args = parser.parse_args()
    create_html_report(args.work_dir)