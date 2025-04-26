web: gunicorn a_core.wsgi:application \
      --bind 0.0.0.0:$PORT \
      --workers 2 \
      --timeout 300
release: python manage.py collectstatic --noinput