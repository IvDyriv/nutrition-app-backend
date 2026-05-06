from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken


class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        raw_access_token = request.COOKIES.get("access_token")

        if raw_access_token is None:
            raw_refresh_token = request.COOKIES.get("refresh_token")

            if raw_refresh_token is None:
                return None

            try:
                refresh = RefreshToken(raw_refresh_token)
                new_access_token = str(refresh.access_token)

                django_request = request._request
                django_request._new_access_token = new_access_token
                django_request._new_refresh_token = str(refresh)

                validated_token = self.get_validated_token(new_access_token)
                return self.get_user(validated_token), validated_token

            except TokenError:
                raise InvalidToken("Refresh token is invalid or expired.")

        try:
            validated_token = self.get_validated_token(raw_access_token)
            return self.get_user(validated_token), validated_token

        except InvalidToken:
            raw_refresh_token = request.COOKIES.get("refresh_token")

            if raw_refresh_token is None:
                raise InvalidToken("Access token expired and refresh token missing.")

            try:
                refresh = RefreshToken(raw_refresh_token)
                new_access_token = str(refresh.access_token)

                django_request = request._request
                django_request._new_access_token = new_access_token
                django_request._new_refresh_token = str(refresh)

                validated_token = self.get_validated_token(new_access_token)
                return self.get_user(validated_token), validated_token

            except TokenError:
                raise InvalidToken("Refresh token is invalid or expired.")