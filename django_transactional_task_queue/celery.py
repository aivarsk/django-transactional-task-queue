from typing import Union
import inspect
import datetime
from django.conf import settings
from functools import wraps
from django_transactional_task_queue.models import Task
from django.utils import timezone

__all__ = ["shared_task"]


def _apply_async(
    func,
    args: tuple = None,
    kwargs: dict = None,
    countdown: float = None,
    execute_at: datetime.datetime = None,
    expires: Union[float, datetime.datetime] = None,
    queue: str = None,
    ignore_result: bool = None,
    add_to_parent: bool = None,
):
    if countdown:
        execute_at = timezone.now() + datetime.timedelta(seconds=int(countdown))
    if expires and isinstance(expires, (int, float)):
        expires = timezone.now() + datetime.timedelta(seconds=int(expires))

    task = Task(
        queue=queue or Task.DEFAULTQ,
        task=".".join((inspect.getmodule(func).__name__, func.__name__)),
        args=args or [],
        kwargs=kwargs or {},
        execute_at=execute_at,
        expires=expires,
    )
    if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
        task.execute()
    else:
        task.save()


class Signature:
    def __init__(self, func, args, kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.parameters = {}

    def set(self, **kwargs):
        self.parameters.update(kwargs)
        return self

    def delay(self):
        _apply_async(self.func, self.args, self.kwargs, **self.parameters)

    def apply_async(self, **kwargs):
        self.parameters.update(kwargs)
        _apply_async(self.func, self.args, self.kwargs, **self.parameters)


def shared_task(func):
    func.delay = lambda *args, **kwargs: _apply_async(func, args, kwargs)
    func.apply_async = lambda *args, **kwargs: _apply_async(func, *args, **kwargs)
    func.s = lambda *args, **kwargs: Signature(func, args, kwargs)
    return func
