# Copyright 2019 Xanadu Quantum Technologies Inc.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A standalone command-line interface for computing quantum programs on a remote
backend.
"""

import sys
import argparse

from strawberryfields.api import Connection
from strawberryfields.api.connection import connection
from strawberryfields.engine import StarshipEngine
from strawberryfields.io import load

def command_line_interface():

    args = parse_arguments()
    ping(args.ping)
    run_program(args.input, args.output)


def ping(args_ping):
    if args_ping:
        connection.ping()
        sys.stdout.write("You have successfully authenticated to the platform!\n")
        sys.exit()

def parse_arguments():
    parser = argparse.ArgumentParser(description="run a blackbird script")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--input", "-i", help="the xbb file to run")
    group.add_argument(
        "--ping", "-p", action="store_true", help="test the API connection"
    )
    parser.add_argument(
        "--output",
        "-o",
        help="where to output the result of the program - outputs to stdout by default",
    )

    return parser.parse_args()

def run_program(args_input, args_output=None):
    program = load(args_input)

    eng = StarshipEngine(program.target)
    sys.stdout.write("Executing program on remote hardware...\n")
    result = eng.run(program)

    if result and result.samples is not None:
        if args.output:
            with open(args_output, "w") as file:
                file.write(str(result.samples))
        else:
            sys.stdout.write(str(result.samples))

