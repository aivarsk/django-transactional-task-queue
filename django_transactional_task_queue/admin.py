from django.contrib import admin, messages

from django_transactional_task_queue.models import DirtyTask, FailedTask, PendingTask

@admin.register(PendingTask)
class PendingTaskAdmin(admin.ModelAdmin):
    list_display = ("id", "execute_at", "queue", "task", "args", "kwargs")
    readonly_fields = (
        "id",
        "created_at",
        "task",
        "args",
        "kwargs",
        "execute_at",
        "retries",
        "traceback",
        "started_at",
        "started",
        "failed",
    )
    list_filter = (
        "queue",
        "task",
        ("execute_at", admin.DateFieldListFilter),
        ("created_at", admin.DateFieldListFilter),
        ("started_at", admin.DateFieldListFilter),
    )

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(DirtyTask, FailedTask)
class RestartableTaskAdmin(admin.ModelAdmin):
    list_display = ("id", "execute_at", "queue", "task", "args", "kwargs")
    readonly_fields = (
        "id",
        "created_at",
        "task",
        "execute_at",
        "retries",
        "traceback",
        "started_at",
        "started",
        "failed",
    )
    list_filter = (
        "queue",
        "task",
        ("execute_at", admin.DateFieldListFilter),
        ("created_at", admin.DateFieldListFilter),
        ("started_at", admin.DateFieldListFilter),
    )
    actions = ("force_retry",)

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return True

    @admin.action(description="Retry selected tasks")
    def force_retry(self, request, queryset):
        count = 0
        for task in queryset.iterator():
            count += 1
            task.retry()
        self.message_user(
            request,
            f"{count} task(s) will be retried",
            messages.SUCCESS,
        )
