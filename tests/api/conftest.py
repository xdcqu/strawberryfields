# Copyright 2020 Xanadu Quantum Technologies Inc.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Test fixtures for strawberryfield.api"""
import pytest

from strawberryfields import Program, ops
from strawberryfields.api import Connection


@pytest.fixture
def prog():
    """Program fixture."""
    prog = Program(2)
    with prog.context as q:
        ops.Dgate(0.5) | q[0]
    return prog


@pytest.fixture
def connection():
    """A mock connection object."""
    return Connection(token="token", host="host", port=123, use_ssl=True)
