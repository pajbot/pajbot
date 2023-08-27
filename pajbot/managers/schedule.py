from typing import Optional, Iterable, Any, Mapping, Callable

import datetime
import logging

from pajbot import utils

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.base import BaseScheduler
from apscheduler.job import Job

log = logging.getLogger(__name__)


class ScheduledJob:
    def __init__(self, job: Job) -> None:
        self.job = job

    def pause(self) -> None:
        self.job.pause()

    def resume(self) -> None:
        self.job.resume()

    def remove(self) -> None:
        self.job.remove()


class ScheduleManager:
    base_scheduler = BackgroundScheduler(daemon=True)

    @staticmethod
    def init() -> None:
        if ScheduleManager.base_scheduler.running:
            log.warning("ScheduleManager had its init function called twice!!!!")
            return

        print(type(ScheduleManager.base_scheduler))
        ScheduleManager.base_scheduler.start()

    @staticmethod
    def execute_now(
        method: Callable[..., Any],
        args: Optional[Iterable[Any]] = None,
        kwargs: Optional[Mapping[str, Any]] = None,
        scheduler: Optional[BaseScheduler] = None,
    ) -> ScheduledJob:
        if scheduler is None:
            scheduler = ScheduleManager.base_scheduler

        job = scheduler.add_job(method, "date", run_date=utils.now(), args=args, kwargs=kwargs)
        return ScheduledJob(job)

    @staticmethod
    def execute_delayed(
        delay: float,
        method: Callable[..., Any],
        args: Optional[Iterable[Any]] = None,
        kwargs: Optional[Mapping[str, Any]] = None,
        scheduler: Optional[BaseScheduler] = None,
    ) -> ScheduledJob:
        if scheduler is None:
            scheduler = ScheduleManager.base_scheduler

        job = scheduler.add_job(
            method, "date", run_date=utils.now() + datetime.timedelta(seconds=delay), args=args, kwargs=kwargs
        )
        return ScheduledJob(job)

    @staticmethod
    def execute_every(
        interval: float,
        method: Callable[..., Any],
        args: Optional[Iterable[Any]] = None,
        kwargs: Optional[Mapping[str, Any]] = None,
        scheduler: Optional[BaseScheduler] = None,
        jitter: Optional[float] = None,
    ) -> ScheduledJob:
        if scheduler is None:
            scheduler = ScheduleManager.base_scheduler

        job = scheduler.add_job(method, "interval", seconds=interval, args=args, kwargs=kwargs, jitter=jitter)
        return ScheduledJob(job)
