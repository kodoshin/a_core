from django.apps import AppConfig


class GitAuthConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'git_auth'

    def ready(self):
        import git_auth.signals
