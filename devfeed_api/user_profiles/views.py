"""Authentication views (register, logout) and the followed-keywords viewset.

Login uses DRF's ObtainAuthToken.
"""

from django.db import transaction
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from .models import UserKeyword
from .serializers import KeywordSerializer, RegisterSerializer


class RegisterView(APIView):
    """POST username, email, and password; returns 201 with an API token."""

    # Sign-up must stay open to anonymous users regardless of the global default
    permission_classes = [AllowAny]

    def post(self, request):
        registration_serializer = RegisterSerializer(data=request.data)
        # Invalid input returns 400 with the field errors
        registration_serializer.is_valid(raise_exception=True)

        # Create the user and their token together, or neither
        with transaction.atomic():
            new_user = registration_serializer.save()
            new_token = Token.objects.create(user=new_user)

        return Response(
            {"username": new_user.username, "token": new_token.key},
            status=status.HTTP_201_CREATED
        )


class LogoutView(APIView):
    """POST with a valid token; deletes it so it can't be used again."""

    # Missing or invalid tokens get 401 before this view runs
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # With TokenAuthentication, request.auth is the caller's Token row
        request.auth.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class KeywordViewSet(ModelViewSet):
    """Each logged-in user can list, create, update and delete only their own keywords."""

    serializer_class = KeywordSerializer
    # Overrides the global IsStaffOrReadOnly default: any logged-in user may
    # write here, and anonymous requests get 401.
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Filtering to the caller's rows makes another user's keyword id a 404.
        # Ordering by keyword keeps paginated pages stable.
        return UserKeyword.objects.filter(user=self.request.user).order_by("keyword")
