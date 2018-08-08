#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 Uninett AS
#
# This file is part of Network Administration Visualized (NAV).
#
# NAV is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License version 2 as published by the Free
# Software Foundation.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
# more details.  You should have received a copy of the GNU General Public
# License along with NAV. If not, see <http://www.gnu.org/licenses/>.
#

from __future__ import print_function

import re
import sys
import email
import configparser

import argparse

from nav.bootstrap import bootstrap_django
bootstrap_django(__file__)

import nav
import nav.mailin
from nav import logs

import logging
logging.raiseExceptions = False
logger = logging.getLogger('nav.mailin')
conf = None


def main():
    global conf

    args = parse_args()

    configfile = nav.buildconf.sysconfdir + '/mailin.conf'
    logfile = nav.buildconf.localstatedir + '/log/mailin.log'

    # Todo: fail if config file is not found
    conf = configparser.ConfigParser()
    conf.read(configfile)

    # Must do this after config, so logfile can be configurable
    if args.test:
        init_logging('-')
    else:
        init_logging(logfile)

    add_mailin_subsystem()

    plugins = conf.get('main', 'plugins').split()
    plugins = load_plugins(plugins)

    if args.init:
        logger.info('Initialization done. Exiting.')
        return

    read_and_process_input(plugins, test=args.test)
    logger.info('Done')


def parse_args():
    """Parse program arguments"""
    parser = argparse.ArgumentParser(
        description="Parse RFC822 formatted mail messages from 3rd party "
                    "software and convert them to NAV events, using plugins",
    )
    parser.add_argument('-i', '--init', action='store_true',
                        help='only load plugins and create event/alert types')
    parser.add_argument('-t', '--test', action='store_true',
                        help='write events to stdout instead of posting them.')
    return parser.parse_args()


def read_and_process_input(plugins, test=False):
    """Parses stdin as e-mail and passes it to each plugin in order"""
    msg = email.message_from_file(sys.stdin)
    logger.info('---')
    logger.info('Got message: From=%r Subject=%r', msg['From'], msg['Subject'])

    for plugin in plugins:
        if plugin.accept(msg):
            logger.info('%s accepted the message', plugin.name)

            if authorize_match(plugin, msg):
                if plugin.authorize(msg):
                    events = plugin.process(msg)
                    if isinstance(events, nav.event.Event):
                        # Only one event, put it in a list
                        events = [events]

                    if test:
                        print('Would have posted these events:')
                        for event in events:
                            print(event)
                    else:
                        for event in events:
                            event.post()
                            logger.info('Posted %r', event)
                else:
                    logger.error('Message not authorized')

            break  # Only one message gets to play


def add_mailin_subsystem():
    """Ensure that the 'mailin' subsystem exists in the db"""

    conn = nav.db.getConnection('default', 'manage')
    cursor = conn.cursor()

    cursor.execute("select * from subsystem where name='mailin'")
    if cursor.rowcount == 0:
        cursor.execute("INSERT INTO subsystem (name, descr) "
                       "VALUES ('mailin', '')")
    conn.commit()


def load_plugins(paths):
    plugins = []

    for path in paths:
        logger.info('Loading plugin %s ...', path)
        parent = path.split('.')[:-1]

        try:
            mod = __import__(path, globals(), locals(), [parent])
        except ImportError:
            logger.error('Plugin not found: %s', path)
        except Exception:
            logger.exception('Failed to load plugin %s', path)
            continue

        plugin = mod.Plugin(path, conf, logger)
        plugins.append(plugin)

    return plugins


def authorize_match(plugin, msg):
    """Test message headers against a pattern in the configuration file"""

    # Try to get 'authorization' option from plugin section or main section
    if conf.has_option(plugin.name, 'authorization'):
        raw = conf.get(plugin.name, 'authorization')
    elif conf.has_option('main', 'authorization'):
        raw = conf.get('main', 'authorization')
    else:
        # No authorization pattern, so just let it through
        return True

    # Return True if the pattern matches at least one header line
    pattern = re.compile(raw)
    for key in msg.keys():
        value = msg[key]
        line = key + ': ' + value
        if pattern.search(line):
            return True

    # Should this logged as error or warning?
    logger.error("Message doesn't match auth pattern %r", raw)
    return False


def init_logging(filename):
    if filename == '-':
        logs.init_stderr_logging()
    else:
        if conf.has_option('main', 'logfile'):
            filename = conf.get('main', 'logfile')
        logs.init_generic_logging(logfile=filename, stderr=False)

if __name__ == '__main__':
    main()
