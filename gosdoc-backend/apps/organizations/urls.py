"""
ГосДок — URL организаций (apps/organizations/urls.py)
Раздел 4.3 ТЗ
"""

from django.urls import path

from .views import (
    OrganizationDetailView,
    OrganizationInviteView,
    OrganizationListCreateView,
    OrganizationMembersView,
)

urlpatterns = [
    path("", OrganizationListCreateView.as_view(), name="organization-list"),
    path("<uuid:pk>/", OrganizationDetailView.as_view(), name="organization-detail"),
    path("<uuid:pk>/members/", OrganizationMembersView.as_view(), name="organization-members"),
    path("<uuid:pk>/invite/", OrganizationInviteView.as_view(), name="organization-invite"),
]
