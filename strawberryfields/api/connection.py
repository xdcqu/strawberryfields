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
"""
This module provides an interface to a remote program execution backend.
"""
from datetime import datetime
import io
import json
import logging
from typing import List

import numpy as np
import requests

from strawberryfields.configuration import DEFAULT_CONFIG
from strawberryfields.io import to_blackbird
from strawberryfields.program import Program

from .job import Job, JobStatus
from .result import Result

log = logging.getLogger(__name__)


class RequestFailedError(Exception):
    """Raised when a request to the remote platform returns an error response."""


class Connection:
    """Manages remote connections to the remote job execution platform and exposes
    various job operations.

    For basic usage, it is not necessary to manually instantiate this object; the user
    is encouraged to use the higher-level interface provided by
    :class:`~strawberryfields.engine.StarshipEngine`.

    **Example:**

    The following example instantiates a :class:`~strawberryfields.api.Connection` for a
    given API authentication token, tests the connection, submits a new job, and
    retrieves an existing job.

    >>> connection = Connection(token="abc")
    >>> success = connection.ping() # `True` if successful, `False` if the connection fails
    >>> job = connection.create_job("chip2", program, shots=123)
    >>> job
    <Job: id=d177cbf5-1816-4779-802f-cef2c117dc1a, ...>
    >>> job.status
    <JobStatus.QUEUED: 'queued'>
    >>> job.result
    AttributeError
    >>> job = connection.get_job(known_job_id)
    >>> job
    <Job: id=59a1c0b1-c6a7-4f9b-ae37-0ac5eec9c413, ...>
    >>> job.status
    <JobStatus.COMPLETED: 'complete'>
    >>> job.result
    [[0 1 0 2 1 0 0 0]]

    Args:
        token (str): the API authentication token
        host (str): the hostname of the remote platform
        port (int): the port to connect to on the remote host
        use_ssl (bool): whether to use SSL for the connection
    """

    # pylint: disable=bad-continuation
    def __init__(
        self,
        token: str,
        host: str = DEFAULT_CONFIG["api"]["hostname"],
        port: int = DEFAULT_CONFIG["api"]["port"],
        use_ssl: bool = DEFAULT_CONFIG["api"]["use_ssl"],
        verbose: bool = False,
    ):
        self._token = token
        self._host = host
        self._port = port
        self._use_ssl = use_ssl
        self._verbose = verbose

        self._base_url = "http{}://{}:{}".format(
            "s" if self.use_ssl else "", self.host, self.port
        )
        self._headers = {"Authorization": self.token}

    @property
    def token(self) -> str:
        """The API authentication token.

        Returns:
            str: the authentication token
        """
        return self._token

    @property
    def host(self) -> str:
        """The host for the remote platform.

        Returns:
            str: the hostname
        """
        return self._host

    @property
    def port(self) -> int:
        """The port to connect to on the remote host.

        Returns:
            int: the port number
        """
        return self._port

    @property
    def use_ssl(self) -> bool:
        """Whether to use SSL for the connection.

        Returns:
            bool: ``True`` if SSL should be used, and ``False`` otherwise
        """
        return self._use_ssl

    def create_job(self, target: str, program: Program, shots: int) -> Job:
        """Creates a job with the given circuit.

        Args:
            target (str): the target device
            program (strawberryfields.Program): the quantum circuit
            shots (int): the number of shots

        Returns:
            strawberryfields.engine.Job: the created job
        """
        # Serialize a blackbird circuit for network transmission
        bb = to_blackbird(program)
        # pylint: disable=protected-access
        bb._target["name"] = target
        # pylint: disable=protected-access
        bb._target["options"] = {"shots": shots}
        circuit = bb.serialize()

        path = "/jobs"
        response = requests.post(
            self._url(path),
            headers=self._headers,
            data=json.dumps({"circuit": circuit}),
        )
        if response.status_code == 201:
            if self._verbose:
                log.info("The job was successfully submitted.")
            return Job(
                id_=response.json()["id"],
                status=JobStatus(response.json()["status"]),
                connection=self,
            )
        raise RequestFailedError(
            "Failed to create job: {}".format(self._format_error_message(response))
        )

    def get_all_jobs(self, after: datetime = datetime(1970, 1, 1)) -> List[Job]:
        """Gets a list of jobs created by the user, optionally filtered by datetime.

        Args:
            after (datetime.datetime): if provided, only jobs more recently created
                then ``after`` are returned

        Returns:
            List[strawberryfields.engine.Job]: the jobs
        """
        raise NotImplementedError("This feature is not yet implemented")

    def get_job(self, job_id: str) -> Job:
        """Gets a job.

        Args:
            job_id (str): the job ID

        Returns:
            strawberryfields.engine.Job: the job
        """
        path = "/jobs/{}".format(job_id)
        response = requests.get(self._url(path), headers=self._headers)
        if response.status_code == 200:
            return Job(
                id_=response.json()["id"],
                status=JobStatus(response.json()["status"]),
                connection=self,
            )
        raise RequestFailedError(
            "Failed to get job: {}".format(self._format_error_message(response))
        )

    def get_job_status(self, job_id: str) -> JobStatus:
        """Returns the status of a job.

        Args:
            job_id (str): the job ID

        Returns:
            strawberryfields.engine.JobStatus: the job status
        """
        return JobStatus(self.get_job(job_id).status)

    def get_job_result(self, job_id: str) -> Result:
        """Returns the result of a job.

        Args:
            job_id (str): the job ID

        Returns:
            strawberryfields.engine.Result: the job result
        """
        path = "/jobs/{}/result".format(job_id)
        response = requests.get(
            self._url(path), headers={"Accept": "application/x-numpy", **self._headers},
        )
        if response.status_code == 200:
            # Read the numpy binary data in the payload into memory
            with io.BytesIO() as buf:
                buf.write(response.content)
                buf.seek(0)
                samples = np.load(buf)
            return Result(samples, is_stateful=False)
        raise RequestFailedError(
            "Failed to get job result: {}".format(self._format_error_message(response))
        )

    def cancel_job(self, job_id: str):
        """Cancels a job.

        Args:
            job_id (str): the job ID
        """
        path = "/jobs/{}".format(job_id)
        response = requests.patch(
            self._url(path),
            headers=self._headers,
            data={"status": JobStatus.CANCELLED.value},
        )
        if response.status_code == 204:
            if self._verbose:
                log.info("The job was successfully cancelled.")
            return
        raise RequestFailedError(
            "Failed to cancel job: {}".format(self._format_error_message(response))
        )

    def ping(self) -> bool:
        """Tests the connection to the remote backend.

        Returns:
            bool: ``True`` if the connection is successful, and ``False`` otherwise
        """
        path = "/healthz"
        response = requests.get(self._url(path), headers=self._headers)
        return response.status_code == 200

    def _url(self, path: str) -> str:
        return self._base_url + path

    @staticmethod
    def _format_error_message(response: requests.Response) -> str:
        body = response.json()
        return "{} ({}): {}".format(
            body.get("status_code", ""), body.get("code", ""), body.get("detail", "")
        )

    def __repr__(self):
        return "<{}: token={}, host={}>".format(
            self.__class__.__name__, self.token, self.host
        )

    def __str__(self):
        return self.__repr__()
