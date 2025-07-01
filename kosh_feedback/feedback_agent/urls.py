from django.urls import path
from . import views

urlpatterns = [
    # API paths only - we use React frontend
    path("api/reports/", views.report_create),
    path("api/query_chatgpt/", views.query_chatgpt),
]