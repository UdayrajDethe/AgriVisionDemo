from django.contrib import admin
from django.urls import path

from accounts import views as account_views


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health", account_views.health, name="health"),
    path("api/dashboard", account_views.dashboard, name="dashboard"),
    path("api/auth/register", account_views.register_user, name="register"),
    path("api/auth/login", account_views.login_user, name="login"),
    path("api/diseases", account_views.diseases, name="diseases"),
    path("api/analysis/history", account_views.history, name="history"),
    path("api/analyze", account_views.analyze_image, name="analyze"),
    path("api/schema/init", account_views.init_schema, name="init_schema"),
]
