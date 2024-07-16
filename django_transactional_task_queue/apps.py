from django.apps import AppConfig


class TransactionalTaskQueueConfig(AppConfig):
    name = "django_transactional_task_queue"
    label = "dttq"
    verbose_name = "Transactional Task Queue"
