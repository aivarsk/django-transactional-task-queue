from django.db import transaction
import time

from django_transactional_task_queue.models import Task
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Process tasks from a queue specified by -Q or 'default'"

    def add_arguments(self, parser):
        parser.add_argument("-Q", action="store", dest="queue_name", help="Queue name")

    def handle(self, *args, **options):
        while True:
            task = Task.next_task(queue=options.get("queue_name"))
            if not task:
                self.stdout.write(self.style.SUCCESS("No new tasks"))
                time.sleep(1)
            else:
                self._execute_one(task)

    def _execute_one(self, task):
        with transaction.atomic():
            args = [str(arg) for arg in task.args]
            args += [str(key) + "=" + str(value) for key, value in task.kwargs.items()]
            self.stdout.write(
                self.style.SUCCESS(
                    f"Processing Task({task.pk}) {task.task}({', '.join(args)})"
                )
            )
            task.lock()

            try:
                task.execute()

                self.stdout.write(self.style.SUCCESS(f"Completed Task({task.pk})"))
                task.delete()
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"Failed Task({task.pk}): {exc!r}"))
                task.fail()
