"""
Module to store the command line and logger functions.

Functions:
    load_logger: Function to define the program logging object.
    load_parser: Function to define the command line arguments.
"""

import logging
import argparse
import argcomplete


def load_parser():
    '''
    Function to define the command line arguments.
    '''

    # Argparse
    parser = argparse.ArgumentParser(
        description='Drone API wrapper to make deployments easier.',
    )

    subparser = parser.add_subparsers(dest='subcommand', help='subcommands')

    wait_subparser = subparser.add_parser('wait')
    wait_subparser.add_argument(
        "build_number",
        nargs='?',
        type=int,
        default=None,
    )

    set_subparser = subparser.add_parser('set')
    set_subparser.add_argument("project_id")

    subparser.add_parser('active')
    subparser.add_parser('verify')
    subparser.add_parser('status')

    promote_subparser = subparser.add_parser('promote')
    promote_subparser.add_argument(
        "build_number",
        nargs='?',
        type=int,
        default=None,
    )
    promote_subparser.add_argument(
        "environment",
        nargs='?',
        type=str,
        choices=['production', 'staging'],
        default='production',
    )
    promote_subparser.add_argument(
        "-w",
        "--wait",
        help="Wait for the promoted job to finish",
        action='store_true',
    )

    argcomplete.autocomplete(parser)
    return parser


def load_logger():
    '''
    Function to define the program logging object.
    '''

    logging.addLevelName(logging.INFO, "[\033[36mINFO\033[0m]")
    logging.addLevelName(logging.ERROR, "[\033[31mERROR\033[0m]")
    logging.addLevelName(logging.DEBUG, "[\033[32mDEBUG\033[0m]")
    logging.addLevelName(logging.WARNING, "[\033[33mWARNING\033[0m]")
    logging.basicConfig(
        level=logging.WARNING,
        format="  %(levelname)s %(message)s",
    )

    return logging.getLogger('main')
