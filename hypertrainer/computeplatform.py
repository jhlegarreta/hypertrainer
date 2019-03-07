import os
import signal
import subprocess
from abc import ABC, abstractmethod
from enum import Enum

from dataclasses import dataclass

from hypertrainer.utils import TaskStatus


@dataclass
class TaskState:
    status: TaskStatus


class ComputePlatform(ABC):
    @abstractmethod
    def submit(self, task):
        """Submit a task and return the plaform specific task id."""
        pass
    
    @abstractmethod
    def monitor(self, task, keys=None):
        """Return information about the task.
        
        Methods that override this method are expected to return the following dict:
        {
            'status': TaskStatus object
            'stdout': str containing the whole stdout
            'stderr': str containing the whole stderr
            'logs': {
                'log_filename.extension': str containing the whole log,
                ...(all other logs)...
            }
        }
        Keys can be a list of dict keys, for example: ['status'], in which case a partial dict is returned. If keys is
        None, the full dict is returned.
        """
        pass

    @abstractmethod
    def cancel(self, task):
        """Cancel a task."""
        pass


class LocalPlatform(ComputePlatform):
    def __init__(self):
        self.processes = {}
    
    def submit(self, task):
        p = subprocess.Popen(['python', task.script_file, task.config_file],
                             stdout=task.stdout_path.open(mode='w'),
                             stderr=task.stderr_path.open(mode='w'),
                             cwd=os.path.dirname(os.path.realpath(__file__)),
                             universal_newlines=True)
        self.processes[p.pid] = p
        return str(p.pid)
    
    def monitor(self, task, keys=None) -> TaskState:
        if keys is not None and (len(keys) >= 2 or 'status' not in keys):
            raise NotImplementedError
        
        p = self.processes.get(int(task.job_id), None)  # type: subprocess.Popen
        if p is None:
            return TaskState(status=TaskStatus.Lost)

        poll_result = p.poll()
        if poll_result is None:
            status = TaskStatus.Running
        else:
            if p.returncode == 0:
                status = TaskStatus.Finished
            elif p.returncode < 0:
                # Negative value: terminated by a signal
                status = TaskStatus.Cancelled
            else:
                status = TaskStatus.Crashed
        return TaskState(status=status)

    def cancel(self, task):
        os.kill(int(task.job_id), signal.SIGTERM)


class ComputePlatformType(Enum):
    LOCAL = 'local'


platform_instances = {  # TODO should instantiate on-demand
    ComputePlatformType.LOCAL: LocalPlatform()
}


def get_platform(p_type: ComputePlatformType):
    return platform_instances[p_type]
