from hypertrainer.computeplatform import ComputePlatformType, get_platform
from hypertrainer.task import Task


class ExperimentManager:
    @staticmethod
    def get_all_tasks():
        # FIXME more efficient db usage
        ExperimentManager.update_statuses()
        all_tasks = list(Task.select())
        return all_tasks

    @staticmethod
    def update_statuses():
        current_platforms = [ComputePlatformType.LOCAL, ComputePlatformType.HELIOS]  # FIXME dynamic
        for ptype in current_platforms:
            platform = get_platform(ptype)
            tasks = Task.select().where(Task.platform_type == ptype)
            job_ids = [t.job_id for t in tasks]
            statuses = platform.get_statuses(job_ids)
            for t in tasks:
                if t.status.is_active():
                    t.status = statuses[t.job_id]
                    t.save()

    @staticmethod
    def submit(platform: str, script_file: str, config_file: str):
        t = Task(script_file, config_file, platform_type=ComputePlatformType(platform))
        t.submit()

    @staticmethod
    def cancel_from_id(task_id):
        if type(task_id) is str:
            t = Task.get(Task.id == task_id)
            if t.status.is_active():
                t.cancel()
        else:
            assert type(task_id) is list
            tasks = Task.select().where(Task.id.in_(task_id))
            for t in tasks:
                if t.status.is_active():
                    t.cancel()  # TODO one bulk ssh command

    @staticmethod
    def delete_from_id(task_id):
        if type(task_id) is str:
            t = Task.get(Task.id == task_id)  # type: Task
            t.delete_instance()
        else:
            assert type(task_id) is list
            Task.delete().where(Task.id.in_(task_id)).execute()


experiment_manager = ExperimentManager()
