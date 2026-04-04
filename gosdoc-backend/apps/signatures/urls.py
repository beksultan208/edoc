from django.urls import path
from .views import SignatureVerifyView

urlpatterns = [
    path("<uuid:pk>/verify/", SignatureVerifyView.as_view(), name="signature-verify"),
]
