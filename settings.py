import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "postgres",
        "USER": "postgres",
        "PASSWORD": "postgres",
        "HOST": "localhost",
        "PORT": "15432",
    }
}
INSTALLED_APPS = ("django_transactional_task_queue",)
# SECRET_KEY = ""
