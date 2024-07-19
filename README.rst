Django Transaction Task Queue
=============================

A short and simple Celery replacement for my Django projects.

* *Database is the only backend.* The task is a simple Django model, it uses the same transaction and connection as other models. No more ``transaction.on_commit`` hooks to schedule tasks.
* *Tasks do not produce any results* and there is no "result backend". If you need to store results, pass a unique key into the task and store the result in some DIY model.
* *You can not wait on the response from the task*, there is no ``get`` or ``join`` to get the task result. I think a thread pool or process pool is better for those requirements.
* *No workflows and chaining of jobs.*
* *ETA (estimated time of arrival) is a first-class citizen.* It does not depend on whether backends support the feature or not.
* *The worker is a single-threaded process*, you start several of those to scale. I have seen too many issues with autoscaling workers, worker processes killed by OS, workers stuck: simple is better.
* *No prefetching or visibility timeouts*. The worker picks the first available task and processes it.
* *Dead letter queue* built in. You get access to failed tasks and can retry them.
* *Django admin for monitoring.* You can view pending tasks, failed, and "dirty" (crashed in the middle of work). Failed and "dirty" tasks can be retried from the same Django admin.   
* *Easy to get the metrics* from Django shell and export to your favorite monitoring tool
* *Task records are removed after successful execution*. Unlike Celery SQLAlchemy's backend, records are removed so you don't have to care about archiving. It also keeps the table small, properly indexed and efficient.
