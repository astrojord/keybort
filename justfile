set dotenv-filename := "env/local.env"

format:
    docker compose exec app ruff format
check:
    docker compose exec app ruff check --fix
check-unsafe:
    docker compose exec app ruff check --fix --unsafe-fixes
test:
    docker compose exec app python manage.py test
empty-migration APP:
    docker compose exec app python manage.py makemigrations {{APP}} --empty
makemigrations *APPS:
    docker compose exec app python manage.py makemigrations {{APPS}}
migrate *APPS:
    docker compose exec app python manage.py migrate {{APPS}}
psql:
    docker compose exec db psql -U $POSTGRES_USER -d $POSTGRES_DB
