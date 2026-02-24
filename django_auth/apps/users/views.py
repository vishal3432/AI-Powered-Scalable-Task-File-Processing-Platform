"""
Django Auth Views
Handles: Registration, Login, Token Refresh, Profile, JWT Validation
"""
import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

from .serializers import UserRegisterSerializer, UserProfileSerializer

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """
    POST /auth/register/
    Register a new user and return JWT tokens.
    """
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = UserRegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "message": "Registration successful.",
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserProfileSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    """
    POST /auth/login/
    Authenticate with email + password, returns JWT tokens.
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            # Enrich with user profile
            from rest_framework_simplejwt.tokens import AccessToken
            token = AccessToken(response.data["access"])
            user = User.objects.get(id=token["user_id"])
            response.data["user"] = UserProfileSerializer(user).data
        return response


class ProfileView(generics.RetrieveUpdateAPIView):
    """
    GET /auth/profile/
    Retrieve or update the authenticated user's profile.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer

    def get_object(self):
        return self.request.user


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def submit_file_for_processing(request):
    """
    POST /auth/files/submit/
    Authenticates the user, then proxies the file to FastAPI for AI processing.
    This is the Django→FastAPI handoff point.
    """
    if "file" not in request.FILES:
        return Response({"error": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)

    uploaded_file = request.FILES["file"]
    task_type = request.data.get("task_type", "summarize")

    # Increment user API call count
    request.user.api_calls_count += 1
    request.user.save(update_fields=["api_calls_count"])

    # Forward file to FastAPI with the user's JWT token
    fastapi_url = f"{settings.FASTAPI_BASE_URL}/process/submit"
    auth_header = request.headers.get("Authorization")

    try:
        fastapi_response = requests.post(
            fastapi_url,
            files={"file": (uploaded_file.name, uploaded_file.read(), uploaded_file.content_type)},
            data={"task_type": task_type, "user_id": request.user.id},
            headers={"Authorization": auth_header},
            timeout=30,
        )
        return Response(fastapi_response.json(), status=fastapi_response.status_code)
    except requests.exceptions.ConnectionError:
        return Response(
            {"error": "AI processing engine is unavailable. Please try again."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except requests.exceptions.Timeout:
        return Response(
            {"error": "Request to AI engine timed out."},
            status=status.HTTP_504_GATEWAY_TIMEOUT,
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def validate_token(request):
    """
    POST /auth/validate-token/
    Internal endpoint used by FastAPI to validate JWT tokens.
    Returns user info if token is valid.
    """
    token_str = request.data.get("token")
    if not token_str:
        return Response({"valid": False, "error": "No token provided"}, status=400)

    try:
        from rest_framework_simplejwt.tokens import AccessToken
        token = AccessToken(token_str)
        user = User.objects.get(id=token["user_id"])
        return Response({
            "valid": True,
            "user_id": user.id,
            "email": user.email,
            "username": user.username,
        })
    except (TokenError, InvalidToken, User.DoesNotExist) as e:
        return Response({"valid": False, "error": str(e)}, status=401)
