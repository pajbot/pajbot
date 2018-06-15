import datetime
import logging

from apscheduler.schedulers.background import BackgroundScheduler

log = logging.getLogger(__name__)


class ScheduledJob:
    def __init__(self, job):
        self.job = job

    def pause(self, *args, **kwargs):
        if self.job:
            self.job.pause(*args, **kwargs)

    def resume(self, *args, **kwargs):
        if self.job:
            self.job.resume(*args, **kwargs)

    def remove(self, *args, **kwargs):
        if self.job:
            self.job.remove(*args, **kwargs)


class ScheduleManager:
    base_scheduler = None

    def init():
        if not ScheduleManager.base_scheduler:
            ScheduleManager.base_scheduler = BackgroundScheduler(daemon=True)
            ScheduleManager.base_scheduler.start()

    def execute_now(method, args=[], kwargs={}, scheduler=None):
        if scheduler is None:
            scheduler = ScheduleManager.base_scheduler

        if scheduler is None:
            return ScheduledJob(None)

        job = scheduler.add_job(method,
                'date',
                run_date=datetime.datetime.now(),
                args=args,
                kwargs=kwargs)
        return ScheduledJob(job)

    def execute_delayed(delay, method, args=[], kwargs={}, scheduler=None):
        if scheduler is None:
            scheduler = ScheduleManager.base_scheduler

        if scheduler is None:
            return ScheduledJob(None)

        job = scheduler.add_job(method,
                'date',
                run_date=datetime.datetime.now() + datetime.timedelta(seconds=delay),
                args=args,
                kwargs=kwargs)
        return ScheduledJob(job)

    def execute_every(interval, method, args=[], kwargs={}, scheduler=None):
        if scheduler is None:
            scheduler = ScheduleManager.base_scheduler

        if scheduler is None:
            return ScheduledJob(None)

        job = scheduler.add_job(method,
                'interval',
                seconds=interval,
                args=args,
                kwargs=kwargs)
        return ScheduledJob(job)
