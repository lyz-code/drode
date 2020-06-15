#!/usr/bin/python3

# Copyright (C) 2020 jmp <jmp@icij.org>
# This file is part of drode.
#
# drode is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# drode is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with drode.  If not, see <http://www.gnu.org/licenses/>.

from drode.cli import load_logger, load_parser

import os
from drode.configuration import Config
config = Config(os.getenv('DRODE_CONFIG', '~/.local/share/drode/config.yaml'))

from drode.manager import DeploymentManager

import sys


def main(argv=sys.argv[1:]):
    parser = load_parser()
    args = parser.parse_args(argv)
    load_logger()

    dm = DeploymentManager()

    if args.subcommand == 'set':
        config.set_active_project(args.project_id)
    elif args.subcommand == 'active':
        print(config.project)
    elif args.subcommand == 'wait':
        dm.wait(args.build_number)
        print('\a')
    elif args.subcommand == 'promote':
        build_number = dm.promote(args.build_number, args.environment)
        if args.wait:
            dm.wait(build_number)
            print('\a')
    elif args.subcommand == 'verify':
        dm.verify()
    elif args.subcommand == 'status':
        dm.status()
