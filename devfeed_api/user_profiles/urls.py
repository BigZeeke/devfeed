"""URL routes for authentication, mounted at /api/auth/."""

from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token
from .views import RegisterView, LogoutView

urlpatterns = [
    # POST username, email, and password -> 201 with a token
    path('register/', RegisterView.as_view(), name='auth-register'),
    # POST username, password -> token for valid credentials, 400 otherwise
    path('token/', obtain_auth_token, name='auth-token'),
    # POST with "Authorization: Token <key>" -> 204, token deleted
    path('logout/', LogoutView.as_view(), name='logout')
]
