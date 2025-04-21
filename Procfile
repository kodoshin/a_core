web: gunicorn a_core.wsgi
release: python manage.py migrate --noinput && python manage.py collectstatic --noinput