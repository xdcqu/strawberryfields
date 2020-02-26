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
This module provides classes for interfacing with program execution jobs on a remote backend.
"""
import enum
import logging

from .result import Result

log = logging.getLogger(__name__)


class InvalidJobOperationError(Exception):
    """Raised when an invalid operation is performed on a job."""


class JobStatus(enum.Enum):
    """Represents the status of a remote job.

    This class maps a set of job statuses to the string representations returned by the
    remote platform.
    """

    OPEN = "open"
    QUEUED = "queued"
    CANCELLED = "cancelled"
    COMPLETED = "complete"
    FAILED = "failed"

    @property
    def is_final(self) -> bool:
        """Checks if this status represents a final and immutable state.

        This method is primarily used to determine if an operation is valid for a given
        status.
        """
        return self in (JobStatus.CANCELLED, JobStatus.COMPLETED, JobStatus.FAILED)


class Job:
    """Represents a remote job that can be queried for its status or result.

    This object should typically not be instantiated directly, but returned by an
    ``Engine`` or ``Connection`` when a job is run.

    Args:
        id_ (str): the job ID
        status (strawberryfields.engine.JobStatus): the job status
        connection (strawberryfields.engine.Connection): the connection over which the
            job is managed
    """

    def __init__(self, id_: str, status: JobStatus, connection: "Connection"):
        self._id = id_
        self._status = status
        self._connection = connection
        self._result = None

    @property
    def id(self) -> str:
        """The job ID."""
        return self._id

    @property
    def status(self) -> JobStatus:
        """The job status."""
        return self._status

    @property
    def result(self) -> Result:
        """The job result.

        This is only defined for completed jobs, and raises an exception for any other
        status.
        """
        if self.status != JobStatus.COMPLETED:
            raise AttributeError(
                "The result is undefined for jobs that are not completed "
                "(current status: {})".format(self.status.value)
            )
        return self._result

    def refresh(self):
        """Refreshes the status of the job, along with the job result if the job is
        newly completed.

        Refreshing only has an effect for open or queued jobs.
        """
        if self.status.is_final:
            log.warning("A %s job cannot be refreshed", self.status.value)
            return
        self._status = self._connection.get_job_status(self.id)
        if self._status == JobStatus.COMPLETED:
            self._result = self._connection.get_job_result(self.id)

    def cancel(self):
        """Cancels the job.

        Only an open or queued job can be cancelled; an exception is raised otherwise.
        """
        if self.status.is_final:
            raise InvalidJobOperationError(
                "A {} job cannot be cancelled".format(self.status.value)
            )
        self._connection.cancel_job(self.id)

    def __repr__(self):
        return "<{}: id={}, status={}>".format(
            self.__class__.__name__, self.id, self.status.value
        )

    def __str__(self):
        return self.__repr__()
