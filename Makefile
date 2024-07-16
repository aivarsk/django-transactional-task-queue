up:
	docker-compose up

upd:
	docker-compose up -d

pgtail:
	MSYS_NO_PATHCONV=1 docker exec -it django-transactional-task-queue-postgres-1 tail -n 0 -f /tmp/postgresql.log

pgshell:
	docker exec -it django-transactional-task-queue-postgres-1 bash -c 'PGPASSWORD=postgres psql -U postgres -h localhost -d postgres'	
