set dotenv-filename := "env/local.env"

format:
    sudo docker compose exec app ruff format
check:
    sudo docker compose exec app ruff check --fix
test:
    sudo docker compose exec app python manage.py test
empty-migration APP:
    sudo docker compose exec app python manage.py makemigrations {{APP}} --empty
makemigrations *APPS:
    sudo docker compose exec app python manage.py makemigrations {{APPS}}
migrate *APPS:
    sudo docker compose exec app python manage.py migrate {{APPS}}
psql:
    sudo docker compose exec db psql -U $POSTGRES_USER -d $POSTGRES_DB
