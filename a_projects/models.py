from django.db import models
from django.contrib.auth.models import User
import re
import tiktoken
from django.db.models import Sum
from cloudinary.models import CloudinaryField



_encoding = tiktoken.get_encoding("cl100k_base")


class Status(models.Model):
    name = models.CharField(max_length=50)
    code = models.IntegerField()

    def __str__(self):
        return self.name


class Technology(models.Model):
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255, blank=True, null=True)
    #image = models.ImageField(upload_to='technologies/', null=True, blank=True)
    image = CloudinaryField('image', blank=True, null=True)
    status = models.ForeignKey(Status, on_delete=models.CASCADE, null=True, blank=True)
    prompt_example = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class Project(models.Model):
    name = models.CharField(max_length=255)
    technology = models.ForeignKey(Technology, on_delete=models.DO_NOTHING, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    git_repo_id = models.CharField(max_length=255, null=True, blank=True)
    git_repo_name = models.CharField(max_length=255)
    git_repo_url = models.URLField()
    status = models.ForeignKey(Status, on_delete=models.CASCADE, null=True, blank=True)
    github_sync = models.BooleanField(default=False)
    tokens_count = models.PositiveIntegerField(default=0)
    is_large = models.BooleanField(default=False)

    def update_tokens(self):
        total = self.file_set.aggregate(total=Sum('tokens_count'))['total'] or 0
        self.tokens_count = total
        super().save(update_fields=['tokens_count', 'is_large'])

    def save(self, *args, **kwargs):
        self.is_large = self.tokens_count > 150_000
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class File(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    path = models.CharField(max_length=255)
    extension = models.CharField(max_length=10)
    content = models.TextField()
    description = models.TextField(blank=True, null=True)
    type = models.CharField(max_length=10)
    header = models.TextField(blank=True, null=True)
    status = models.ForeignKey(Status, on_delete=models.CASCADE, null=True, blank=True)
    last_modified = models.DateTimeField(auto_now=True, null=True, blank=True)
    tokens_count = models.PositiveIntegerField(default=0)
    def extract_header(self):
        if self.extension == '.py':
            # Extrait les lignes d'importation dans un fichier Python
            imports = re.findall(r'^\s*(import\s+\S+|from\s+\S+\s+import\s+\S+)', self.content, re.MULTILINE)
            return '\n'.join(imports)
        elif self.extension == '.html':
            # Extrait les balises {% extends ... %} dans un fichier HTML Django
            extends = re.search(r'{%\s*extends\s+["\']([^"\']+)["\']\s*%}', self.content)
            return extends.group(0) if extends else None
        return None

    def save(self, *args, **kwargs):
        raw = self.content or ''
        self.tokens_count = len(_encoding.encode(raw))
        super().save(*args, **kwargs)
        # Met à jour le total de tokens du projet
        self.project.update_tokens()

    def __str__(self):
        return self.name


class ComponentType(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)
    technology = models.ForeignKey(Technology, on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return self.name


class Component(models.Model):
    file = models.ForeignKey('File', on_delete=models.CASCADE, related_name='components')
    component_type = models.ForeignKey(ComponentType, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    content = models.TextField()
    description = models.TextField(blank=True, null=True)
    start_line = models.IntegerField(null=True, blank=True)
    end_line = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.component_type.name})"
