import datetime
import traceback

from django.db import models, transaction
from django.utils import timezone


class Task(models.Model):
    DEFAULTQ = "default"

    created_at = models.DateTimeField(auto_now_add=True)

    queue = models.CharField(max_length=64)

    task = models.CharField(max_length=256)
    args = models.JSONField()
    kwargs = models.JSONField()

    execute_at = models.DateTimeField(auto_now_add=True)
    expires = models.DateTimeField(null=True, blank=True)

    retries = models.PositiveIntegerField(default=0)
    traceback = models.TextField(null=True, blank=True)

    started_at = models.DateTimeField(null=True, blank=True)
    started = models.BooleanField(default=False)
    failed = models.BooleanField(default=False)

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

                if task.expires and task.expires <= timezone.now():
                    task.delete()
                else:
                    task.started = True
                    task.started_at = timezone.now()
                    task.save(update_fields=["started", "started_at"])
                    return task

    def lock(self):
        """Place a lock as an indicator that worker is still alive"""
        Task.objects.select_for_update().only('id').get(pk=self.pk)

    def fail(self):
        self.started = False
        self.failed = True
        self.traceback = traceback.format_exc()
        self.save(update_fields=["started", "failed", "traceback"])

    def retry(self):
        self.started = False
        self.failed = False
        self.traceback = None
        self.retries = models.F("retries") + 1
        # Do not stay in the front of the queue
        self.execute_at = timezone.now()
        self.save(update_fields=["started", "failed", "traceback", "retries", "execute_at"])

    def execute(self):
        last_dot = self.task.rindex(".")
        mod = self.task[:last_dot]
        fun = self.task[last_dot + 1 :]

        f = getattr(__import__(mod, fromlist=(fun,)), fun)
        f(*self.args, **self.kwargs)

    class Meta:
        indexes = [
            models.Index(
                name="dttq_task_execute_at_queue_idx",
                fields=("execute_at", "queue"),
                condition=models.Q(failed=False, started=False),
            )
        ]


class PendingTaskManager(models.Manager):
    def get_queryset(self):
        return (
            super().get_queryset().filter(failed=False, started=False).order_by("execute_at")
        )


class PendingTask(Task):
    objects = PendingTaskManager()

    class Meta:
        proxy = True


class DirtyTaskManager(models.Manager):
    def get_queryset(self):
        with transaction.atomic():
            # Get tasks that have been started but are not locked by worker
            # Ignore tasks started just now because there is a gap between
            # picking the task for processing and locking/working on it by the worker
            pks = list(
                super()
                .get_queryset()
                .select_for_update(skip_locked=True)
                .filter(
                    started=True,
                    started_at__lte=timezone.now() - datetime.timedelta(seconds=10),
                )
                .values_list("pk", flat=True)
            )
        return super().get_queryset().filter(pk__in=pks)


class DirtyTask(Task):
    objects = DirtyTaskManager()

    class Meta:
        proxy = True


class FailedTaskManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(failed=True)


class FailedTask(Task):
    objects = FailedTaskManager()

    class Meta:
        proxy = True
