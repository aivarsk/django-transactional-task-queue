import datetime
import traceback

from django.db import models, transaction
from django.utils import timezone
from picklefield.fields import PickledObjectField


class MaxRetriesExceededError(Exception): ...


class Retry(Exception):
    exc = None
    execute_at = None
    max_retries = None

    def __init__(self, exc=None, execute_at=None, max_retries=None):
        super().__init__()
        self.exc = exc
        self.execute_at = execute_at
        self.max_retries = max_retries


class Task(models.Model):
    DEFAULTQ = "default"
    queue = models.CharField(max_length=64)

    func = models.CharField(max_length=256)
    args = PickledObjectField()
    kwargs = PickledObjectField()
    repr = models.CharField(max_length=512)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    execute_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    alive_at = models.DateTimeField(null=True, blank=True, editable=False)

    retries = models.PositiveIntegerField(default=0, editable=False)
    traceback = models.TextField(null=True, blank=True, editable=False)

    started = models.BooleanField(default=False, editable=False)
    failed = models.BooleanField(default=False, editable=False)

    def save(self, *args, **kwargs):
        strargs = [str(arg) for arg in self.args]
        strargs += [str(key) + "=" + str(value) for key, value in self.kwargs.items()]
        self.repr = f"{self.func}({', '.join(strargs)})"
        super().save(*args, **kwargs)

    @classmethod
    def next_task(cls, queue=None):
        queue = queue or "default"
        while True:
            with transaction.atomic():
                task = (
                    cls.objects.select_for_update(skip_locked=True)
                    .filter(
                        failed=False,
                        started=False,
                        execute_at__lte=timezone.now(),
                        queue=queue,
                    )
                    .order_by("execute_at")
                    .first()
                )
                if not task:
                    return task

                if task.expires_at and task.expires_at <= timezone.now():
                    task.delete()
                else:
                    task.started = True
                    task.alive_at = timezone.now()
                    task.save(update_fields=["started", "alive_at"])
                    return task

    @classmethod
    def alive(cls, task_id):
        cls.objects.filter(pk=task_id).update(alive_at=timezone.now())

    def fail(self, exc):
        self.started = False
        self.failed = True
        self.traceback = traceback.format_exception(exc)
        self.save(update_fields=["started", "failed", "traceback"])

    def retry(self, retry_info: Retry):

        self.retries += 1
        if retry_info.max_retries is not None and self.retries > retry_info.max_retries:
            if retry_info.exc:
                self.fail(retry_info.exc)
            else:
                self.fail(MaxRetriesExceededError())
            return False

        self.started = False
        self.failed = False
        if retry_info.exc:
            self.traceback = traceback.format_exception(retry_info.exc)
        else:
            self.traceback = None
        self.execute_at = retry_info.execute_at
        self.save(
            update_fields=["started", "failed", "traceback", "retries", "execute_at"]
        )
        return True

    def execute(self):
        last_dot = self.func.rindex(".")
        mod = self.func[:last_dot]
        func = self.func[last_dot + 1 :]

        f = getattr(__import__(mod, fromlist=(func,)), func)
        f(*self.args, **self.kwargs)

    class Meta:
        indexes = [
            models.Index(
                name="taskq_execute_at_queue_idx",
                fields=("execute_at", "queue"),
                condition=models.Q(failed=False, started=False),
            )
        ]


class PendingTaskManager(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(failed=False, started=False, execute_at__lte=timezone.now())
            .order_by("execute_at")
        )


class PendingTask(Task):
    objects = PendingTaskManager()

    class Meta:  # pyright: ignore [reportIncompatibleVariableOverride]
        proxy = True


class FutureTaskManager(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(failed=False, started=False, execute_at__gt=timezone.now())
            .order_by("execute_at")
        )


class FutureTask(Task):
    objects = FutureTaskManager()

    class Meta:  # pyright: ignore [reportIncompatibleVariableOverride]
        proxy = True


class ActiveTaskManager(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(
                started=True,
                alive_at__gt=timezone.now() - datetime.timedelta(seconds=3),
            )
        )


class ActiveTask(Task):
    objects = ActiveTaskManager()

    class Meta:  # pyright: ignore [reportIncompatibleVariableOverride]
        proxy = True


class DirtyTaskManager(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(
                started=True,
                alive_at__lte=timezone.now() - datetime.timedelta(seconds=3),
            )
        )


class DirtyTask(Task):
    objects = DirtyTaskManager()

    class Meta:  # pyright: ignore [reportIncompatibleVariableOverride]
        proxy = True


class FailedTaskManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(failed=True)


class FailedTask(Task):
    objects = FailedTaskManager()

    class Meta:  # pyright: ignore [reportIncompatibleVariableOverride]
        proxy = True
