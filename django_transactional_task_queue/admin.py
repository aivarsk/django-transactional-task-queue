from django.contrib import admin, messages

from django_transactional_task_queue.models import DirtyTask, FailedTask, PendingTask


class PendingTaskAdmin(admin.ModelAdmin):
    list_display = ("id", "eta", "queue", "task", "args", "kwargs")
    readonly_fields = (
        "id",
        "created_at",
        "task",
        "args",
        "kwargs",
        "eta",
        "retries",
        "traceback",
        "started_at",
        "started",
        "failed",
    )
    list_filter = (
        "queue",
        "task",
        ("eta", admin.DateFieldListFilter),
        ("created_at", admin.DateFieldListFilter),
        ("started_at", admin.DateFieldListFilter),
    )

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class DirtyTaskAdmin(admin.ModelAdmin):
    list_display = ("id", "eta", "queue", "task", "args", "kwargs")
    readonly_fields = (
        "id",
        "created_at",
        "task",
        "eta",
        "retries",
        "traceback",
        "started_at",
        "started",
        "failed",
    )
    list_filter = (
        "queue",
        "task",
        ("eta", admin.DateFieldListFilter),
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


class FailedTaskAdmin(admin.ModelAdmin):
    list_display = ("id", "eta", "queue", "task", "args", "kwargs")
    readonly_fields = (
        "id",
        "created_at",
        "task",
        "eta",
        "retries",
        "traceback",
        "started_at",
        "started",
        "failed",
    )
    list_filter = (
        "queue",
        "task",
        ("eta", admin.DateFieldListFilter),
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


admin.site.register(PendingTask, PendingTaskAdmin)
admin.site.register(DirtyTask, DirtyTaskAdmin)
admin.site.register(FailedTask, FailedTaskAdmin)
