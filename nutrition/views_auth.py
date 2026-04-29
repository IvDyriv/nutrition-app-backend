from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from nutrition.serializers_auth import (
    ChangePasswordSerializer,
    LoginSerializer,
    LogoutSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    UserSerializer,
)
from nutrition.services.auth import (
    request_password_reset,
    reset_password_by_token,
    send_registration_verification,
    verify_email_token,
)


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

        send_registration_verification(user)

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
        is_verified, message = verify_email_token(token)

        return Response(
            {"detail": message},
            status=status.HTTP_200_OK if is_verified else status.HTTP_400_BAD_REQUEST,
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
        request_password_reset(email)

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

        if not reset_password_by_token(token=token, new_password=new_password):
            return Response(
                {"detail": "Invalid reset token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"detail": "Password has been reset successfully."},
            status=status.HTTP_200_OK,
        )
