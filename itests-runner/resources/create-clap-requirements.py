#!/usr/bin/env python
import json

with open('/tmp/config.json', 'r') as f:
    config = json.load(f)

print "#Using this config: {0}".format(config)

repositories = config['repositories']
requirements = '\n'.join('{0}@{1}'.format(key, value)
                         for key, value in repositories.iteritems())

with open('/tmp/clap-requirements.txt', 'w') as f:
    f.write(requirements)
