from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import permissions, status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from nutrition.serializers_auth import (
    RegisterSerializer,
    UserSerializer,
    LogoutSerializer,
    LoginSerializer,
    ChangePasswordSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer)
import secrets
from django.utils import timezone
from rest_framework.permissions import AllowAny
from .models import UserProfile
from .services.email_service import send_welcome_email, send_verification_email, send_password_reset_email



@extend_schema(
    summary="Register user",
    description="Creates a new user account and sends welcome + verification email.",
    request=RegisterSerializer,
    responses={201: UserSerializer},
)
class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        profile = user.profile
        profile.is_verified = False
        profile.verified_at = None
        profile.verification_token = secrets.token_urlsafe(32)
        profile.save()

        send_welcome_email(user)
        send_verification_email(user, profile.verification_token)

        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


@extend_schema(
    summary="Login user",
    description="Returns JWT access and refresh tokens.",
)
class LoginView(TokenObtainPairView):
    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer


@extend_schema(
    summary="Refresh token",
    description="Returns new access token and rotated refresh token.",
)
class RefreshView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]


@extend_schema(
    summary="Current user",
    description="Returns currently authenticated user.",
    responses={200: UserSerializer},
)
class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)


class LogoutView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LogoutSerializer

    @extend_schema(
        request=LogoutSerializer,
        responses={204: None},
        summary="Logout user",
        description="Blacklists refresh token.",
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        refresh_token = serializer.validated_data["refresh"]
        token = RefreshToken(refresh_token)
        token.blacklist()

        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    summary="Verify email",
    description="Verifies user email by token.",
    responses={200: None, 400: None},
)
class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        token = request.query_params.get("token")

        if not token:
            return Response(
                {"detail": "Verification token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            profile = UserProfile.objects.get(verification_token=token)
        except UserProfile.DoesNotExist:
            return Response(
                {"detail": "Invalid verification token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        profile.is_verified = True
        profile.verified_at = timezone.now()
        profile.verification_token = None
        profile.save()

        return Response(
            {"detail": "Email verified successfully."},
            status=status.HTTP_200_OK,
        )


@extend_schema(
    summary="Change password",
    description="Changes password of authenticated user.",
    request=ChangePasswordSerializer,
    responses={200: None},
)
@extend_schema(
    summary="Change password",
    description="Changes password of authenticated user.",
    request=ChangePasswordSerializer,
    responses={200: None},
)
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        user = request.user
        old_password = serializer.validated_data["old_password"]
        new_password = serializer.validated_data["new_password"]

        if not user.check_password(old_password):
            return Response(
                {"old_password": ["Old password is incorrect."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save()

        return Response(
            {"detail": "Password changed successfully."},
            status=status.HTTP_200_OK,
        )


@extend_schema(
    summary="Request password reset",
    description="Send password reset email if account exists.",
    request=PasswordResetRequestSerializer,
    responses={200: None},
)
class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        User = get_user_model()

        user = User.objects.filter(email=email).first()

        if user and hasattr(user, "profile"):
            token = secrets.token_urlsafe(32)
            profile = user.profile
            profile.password_reset_token = token
            profile.password_reset_requested_at = timezone.now()
            profile.save()

            send_password_reset_email(user, token)

        return Response(
            {
                "detail": (
                    "If an account with this email exists, "
                    "a password reset email has been sent."
                )
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(
    summary="Confirm password reset",
    description="Reset password using token from email.",
    request=PasswordResetConfirmSerializer,
    responses={200: None},
)
@extend_schema(
    summary="Confirm password reset",
    description="Resets password using reset token.",
    request=PasswordResetConfirmSerializer,
    responses={200: None},
)
class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]

        profile = (
            UserProfile.objects
            .filter(password_reset_token=token)
            .select_related("user")
            .first()
        )

        if not profile:
            return Response(
                {"detail": "Invalid reset token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = profile.user
        user.set_password(new_password)
        user.save()

        profile.password_reset_token = None
        profile.password_reset_requested_at = None
        profile.save(update_fields=["password_reset_token", "password_reset_requested_at"])

        return Response(
            {"detail": "Password has been reset successfully."},
            status=status.HTTP_200_OK,
        )