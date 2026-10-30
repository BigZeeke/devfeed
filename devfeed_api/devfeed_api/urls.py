"""
URL configuration for devfeed_api project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    # Register, token (login), and logout endpoints
    path('api/auth/', include('user_profiles.urls')),
    # Sources, tags, and articles
    path('api/', include('articles.urls')),
    # Followed keywords for the logged-in user
    path('api/', include('user_profiles.keyword_urls')),
]
