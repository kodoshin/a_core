from django.urls import path
from .views import code_chat_view, update_default_project, update_default_chatcategory, delete_chat

urlpatterns = [
    path('kenshi/', code_chat_view, name="code_chat_view"),
    path('update_default_project/', update_default_project, name='update_default_project'),
    path('update_default_chatcategory/', update_default_chatcategory, name="update_default_chatcategory"),
    path('delete_chat/', delete_chat, name='delete_chat'),
]