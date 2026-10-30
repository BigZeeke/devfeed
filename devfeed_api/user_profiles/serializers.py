"""Serializers for user registration and followed keywords."""

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import UserKeyword


class RegisterSerializer(serializers.ModelSerializer):
    """Validates sign-up data and creates a user with a hashed password."""

    # Accept the password on input, never return it in a response
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("username", "email", "password")

    def validate(self, attributes):
        # Run Django's AUTH_PASSWORD_VALIDATORS; an unsaved User lets the similarity validator compare the password to the username and email
        candidate_user = User(
            username=attributes.get("username"),
            email=attributes.get("email"),
        )
        try:
            validate_password(attributes["password"], user=candidate_user)
        except DjangoValidationError as password_error:
            # Convert Django's error into DRF's so the client gets a 400, not a 500
            raise serializers.ValidationError(
                {"password": list(password_error.messages)})
        return attributes

    def create(self, validated_data):
        # create_user hashes the password before saving
        return User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
        )


class KeywordSerializer(serializers.ModelSerializer):
    """A keyword the logged-in user follows, with a weight for ranking."""

    # Same pattern as BookmarkSerializer: the owner comes from the logged-in
    # user, and DRF can still check the unique user+keyword constraint, so a
    # duplicate returns 400 instead of a database 500.
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = UserKeyword
        fields = ["id", "user", "keyword", "weight"]

    def validate_keyword(self, keyword_value):
        # DRF's CharField already trims spaces and rejects blanks; lowercasing
        # here makes "Python" and "python" the same keyword. Field validation
        # runs before the unique check, so the check sees the lowercased value.
        return keyword_value.lower()
