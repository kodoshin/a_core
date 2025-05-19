web: gunicorn a_core.wsgi:application \
      --bind 0.0.0.0:$PORT \
      --workers 2 \
      --threads 4 \
      --timeout 300 \
      --worker-class gthread
release: python manage.py collectstatic --noinput