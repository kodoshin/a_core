from django.db import models
from a_projects.models import Project
from management.models import AIModel, APIKey
from django.contrib.auth.models import User
import uuid


class InsightChatCategory(models.Model):
    name = models.CharField(max_length=20)
    type = models.CharField(max_length=15, blank=True, null=True)
    price = models.IntegerField(blank=True, null=True)
    price_secondary_prompt = models.IntegerField(blank=True, null=True)
    discount_percentage = models.IntegerField(default=0)
    is_advanced = models.BooleanField(default=False)
    is_large = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    speed = models.IntegerField(default=0)  # note /10
    precision = models.IntegerField(default=0)  # note /10
    use_cases = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.type}"


class InsightChat(models.Model):
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='insight_chat_user')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='insight_chat_project')
    created_on = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    ai_model = models.ForeignKey(AIModel, on_delete=models.DO_NOTHING, blank=True, null=True)
    rate = models.PositiveSmallIntegerField(default=0, null=True, blank=True, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')])
    prompts_count = models.IntegerField(default=0)
    chat_category = models.ForeignKey(InsightChatCategory, on_delete=models.DO_NOTHING, blank=True, null=True)
    regeneration_count = models.PositiveSmallIntegerField(default=0)
    important = models.BooleanField(default=False)

    def __str__(self):
        return f"InsightChat {self.id} - User: {self.user.username}"

    #class Meta:
    #    ordering = ['created_on']


class InsightTokenUsage(models.Model):
    prompt = models.TextField()
    tokens_used = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    insight_chat = models.ForeignKey(InsightChat, on_delete=models.CASCADE, blank=True, null=True, related_name='tokens_insight_chat')


class InsightProcessingStep(models.Model):
    name = models.CharField(max_length=50, blank=True, null=True)
    short_name = models.CharField(max_length=20, blank=True, null=True)
    description = models.CharField(max_length=100, blank=True, null=True)
    order = models.IntegerField(blank=True, null=True)
    related_function = models.CharField(max_length=50, blank=True, null=True)
    chat_category = models.ForeignKey(InsightChatCategory, on_delete=models.CASCADE, blank=True, null=True, related_name='insight_chat_category_processing_step')

    def __str__(self):
        return f"{self.chat_category} : {self.order}"


class InsightChatMessage(models.Model):
    MESSAGE_TYPE_CHOICES = [
        ('prompt', 'Prompt'),
        ('r-prompt', 'R-Prompt'),
        ('gpt-a', 'GPT Answer'),
        ('gpt-q', 'GPT Question'),
        ('ai', 'AI Processing'),
        ('none', 'None'),
        ('no-components', 'No components'),
    ]
    MESSAGE_STATUS_CHOICES = [
        ('success', 'Success'),
        ('none', 'None'),
        ('no-components', 'No components'),
    ]

    chat = models.ForeignKey(InsightChat, on_delete=models.CASCADE, related_name='messages')
    type = models.CharField(max_length=15, choices=MESSAGE_TYPE_CHOICES)
    status = models.CharField(max_length=15, choices=MESSAGE_STATUS_CHOICES, blank=True, null=True)
    content = models.TextField()
    order = models.IntegerField(blank=True, null=True)
    api_key = models.ForeignKey(APIKey, on_delete=models.DO_NOTHING, blank=True, null=True)
    processing_step = models.ForeignKey(InsightProcessingStep, on_delete=models.CASCADE, related_name='messages', blank=True, null=True)
    created_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    ai_formatting = models.BooleanField(default=False, null=True, blank=True)
    attempt_number = models.PositiveSmallIntegerField(default=1)

    def __str__(self):
        return f"Message {self.id} - Type: {self.type}"


class InsightProcessingError(models.Model):
    insight_chat = models.ForeignKey(
        InsightChat,
        on_delete=models.CASCADE,
        related_name='insight_processing_errors'
    )
    error_content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Error in chat {self.insight_chat_id}: {self.error_content[:50]}"

