"""
ГосДок — Тесты подписей (tests/test_signatures.py)
Разделы 4.7, 2.7 ТЗ: электронная подпись, верификация.

Сценарии:
- Подписать документ (signer/owner → 201, viewer → 403)
- Повторная подпись → 409 Conflict
- Подпись архивного/подписанного документа → 400
- Список подписей документа
- Верификация конкретной подписи
- Документ блокируется когда все signer-ы подписали
"""

import pytest
from unittest.mock import patch

from tests.factories import (
    DocumentFactory,
    SignatureFactory,
    UserFactory,
    WorkspaceFactory,
    WorkspaceMemberFactory,
)

SIGN_PAYLOAD = {
    "signature_data": (
        "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAY"
        "AAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    ),
}


# ============================================================
# Вспомогательная настройка кабинета с подписантом
# ============================================================

def _make_signer_setup(status="draft"):
    """
    Возвращает (owner, signer, workspace, document).
    owner  → role=owner
    signer → role=signer
    document в указанном статусе
    """
    owner = UserFactory()
    signer = UserFactory()
    ws = WorkspaceFactory(created_by=owner)
    WorkspaceMemberFactory(workspace=ws, user=owner, role="owner")
    WorkspaceMemberFactory(workspace=ws, user=signer, role="signer")
    doc = DocumentFactory(workspace=ws, uploaded_by=owner, status=status)
    return owner, signer, ws, doc


def _auth_client_for(user):
    """Создаёт APIClient, авторизованный от имени user."""
    from rest_framework.test import APIClient
    from rest_framework_simplejwt.tokens import RefreshToken

    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


# ============================================================
# POST /api/v1/documents/{id}/sign/
# ============================================================

@pytest.mark.django_db
class TestSignDocument:

    def test_owner_can_sign(self):
        """Владелец кабинета может подписать документ."""
        owner, _, _, doc = _make_signer_setup()
        client = _auth_client_for(owner)

        response = client.post(f"/api/v1/documents/{doc.pk}/sign/", SIGN_PAYLOAD)

        assert response.status_code == 201
        assert "signature" in response.data

    def test_signer_can_sign(self):
        """Подписант (role=signer) может подписать документ."""
        _, signer, _, doc = _make_signer_setup()
        client = _auth_client_for(signer)

        response = client.post(f"/api/v1/documents/{doc.pk}/sign/", SIGN_PAYLOAD)

        assert response.status_code == 201

    def test_viewer_cannot_sign(self):
        """Наблюдатель (role=viewer) не может подписать документ."""
        owner = UserFactory()
        viewer = UserFactory()
        ws = WorkspaceFactory(created_by=owner)
        WorkspaceMemberFactory(workspace=ws, user=owner, role="owner")
        WorkspaceMemberFactory(workspace=ws, user=viewer, role="viewer")
        doc = DocumentFactory(workspace=ws, uploaded_by=owner)

        client = _auth_client_for(viewer)
        response = client.post(f"/api/v1/documents/{doc.pk}/sign/", SIGN_PAYLOAD)

        assert response.status_code == 403

    def test_double_sign_returns_409(self):
        """Повторная подпись одним пользователем возвращает 409."""
        _, signer, _, doc = _make_signer_setup()
        client = _auth_client_for(signer)

        # Первая подпись
        client.post(f"/api/v1/documents/{doc.pk}/sign/", SIGN_PAYLOAD)
        # Вторая
        response = client.post(f"/api/v1/documents/{doc.pk}/sign/", SIGN_PAYLOAD)

        assert response.status_code == 409

    def test_sign_archived_document_returns_400(self):
        """Подпись архивного документа возвращает 400."""
        _, signer, _, doc = _make_signer_setup(status="archived")
        client = _auth_client_for(signer)

        response = client.post(f"/api/v1/documents/{doc.pk}/sign/", SIGN_PAYLOAD)

        assert response.status_code == 400

    def test_sign_already_signed_document_returns_400(self):
        """Документ со статусом signed заблокирован (400)."""
        _, signer, _, doc = _make_signer_setup(status="signed")
        client = _auth_client_for(signer)

        response = client.post(f"/api/v1/documents/{doc.pk}/sign/", SIGN_PAYLOAD)

        assert response.status_code == 400

    def test_sign_requires_auth(self):
        """Подпись без авторизации — 401."""
        from rest_framework.test import APIClient
        _, _, _, doc = _make_signer_setup()

        response = APIClient().post(f"/api/v1/documents/{doc.pk}/sign/", SIGN_PAYLOAD)

        assert response.status_code == 401

    def test_non_member_cannot_sign(self):
        """Пользователь не из кабинета получает 404."""
        _, _, _, doc = _make_signer_setup()
        stranger = UserFactory()
        client = _auth_client_for(stranger)

        response = client.post(f"/api/v1/documents/{doc.pk}/sign/", SIGN_PAYLOAD)

        assert response.status_code == 404

    def test_all_signers_signed_marks_document_signed(self):
        """
        Когда все signer-ы подписали — документ переходит в статус signed.
        Раздел 2.7 ТЗ: подписанный документ блокируется.
        """
        owner, signer, ws, doc = _make_signer_setup()

        # Подписываем owner
        _auth_client_for(owner).post(f"/api/v1/documents/{doc.pk}/sign/", SIGN_PAYLOAD)
        # Подписываем signer (последний требуемый)
        response = _auth_client_for(signer).post(
            f"/api/v1/documents/{doc.pk}/sign/", SIGN_PAYLOAD
        )

        assert response.status_code == 201
        assert response.data["document_fully_signed"] is True

        doc.refresh_from_db()
        assert doc.status == "signed"

    def test_sign_missing_signature_data_returns_400(self):
        """Подпись без данных signature_data возвращает 400."""
        _, signer, _, doc = _make_signer_setup()
        client = _auth_client_for(signer)

        response = client.post(f"/api/v1/documents/{doc.pk}/sign/", {})

        assert response.status_code == 400


# ============================================================
# GET /api/v1/documents/{id}/signatures/
# ============================================================

@pytest.mark.django_db
class TestSignatureListView:

    def test_member_can_list_signatures(self):
        """Участник кабинета видит список подписей документа."""
        owner, signer, ws, doc = _make_signer_setup()
        SignatureFactory(document=doc, user=signer, ip_address="127.0.0.1")

        client = _auth_client_for(owner)
        response = client.get(f"/api/v1/documents/{doc.pk}/signatures/")

        assert response.status_code == 200
        assert len(response.data) >= 1

    def test_list_requires_auth(self):
        """Список подписей без авторизации — 401."""
        from rest_framework.test import APIClient
        _, _, _, doc = _make_signer_setup()

        response = APIClient().get(f"/api/v1/documents/{doc.pk}/signatures/")

        assert response.status_code == 401

    def test_non_member_gets_404(self):
        """Не-участник получает 404."""
        _, _, _, doc = _make_signer_setup()
        stranger = UserFactory()
        client = _auth_client_for(stranger)

        response = client.get(f"/api/v1/documents/{doc.pk}/signatures/")

        assert response.status_code == 404

    def test_empty_list_for_unsigned_document(self):
        """У неподписанного документа список подписей пуст."""
        owner, _, _, doc = _make_signer_setup()
        client = _auth_client_for(owner)

        response = client.get(f"/api/v1/documents/{doc.pk}/signatures/")

        assert response.status_code == 200
        assert response.data == []


# ============================================================
# GET /api/v1/signatures/{id}/verify/
# ============================================================

@pytest.mark.django_db
class TestSignatureVerifyView:

    def test_member_can_verify(self):
        """Участник кабинета может верифицировать подпись."""
        owner, signer, ws, doc = _make_signer_setup()
        sig = SignatureFactory(document=doc, user=signer, ip_address="10.0.0.1")

        client = _auth_client_for(owner)
        response = client.get(f"/api/v1/signatures/{sig.pk}/verify/")

        assert response.status_code == 200
        assert response.data["is_valid"] is True
        assert str(response.data["id"]) == str(sig.pk)
        assert "signer" in response.data
        assert "signed_at" in response.data

    def test_verify_requires_auth(self):
        """Верификация без авторизации — 401."""
        from rest_framework.test import APIClient
        _, signer, _, doc = _make_signer_setup()
        sig = SignatureFactory(document=doc, user=signer, ip_address="10.0.0.1")

        response = APIClient().get(f"/api/v1/signatures/{sig.pk}/verify/")

        assert response.status_code == 401

    def test_non_member_gets_404(self):
        """Не-участник получает 404 при верификации."""
        _, signer, _, doc = _make_signer_setup()
        sig = SignatureFactory(document=doc, user=signer, ip_address="10.0.0.1")
        stranger = UserFactory()
        client = _auth_client_for(stranger)

        response = client.get(f"/api/v1/signatures/{sig.pk}/verify/")

        assert response.status_code == 404

    def test_verify_response_structure(self):
        """Ответ верификации содержит все обязательные поля."""
        owner, signer, ws, doc = _make_signer_setup()
        sig = SignatureFactory(document=doc, user=signer, ip_address="192.168.1.1")

        client = _auth_client_for(owner)
        response = client.get(f"/api/v1/signatures/{sig.pk}/verify/")

        assert response.status_code == 200
        required_fields = {"id", "is_valid", "document", "signer", "signed_at", "ip_address"}
        assert required_fields.issubset(set(response.data.keys()))


# ============================================================
# Модель Signature
# ============================================================

@pytest.mark.django_db
class TestSignatureModel:

    def test_signature_str(self):
        """__str__ возвращает читаемое описание."""
        _, signer, _, doc = _make_signer_setup()
        sig = SignatureFactory(document=doc, user=signer, ip_address="127.0.0.1")
        result = str(sig)
        assert "Подпись" in result

    def test_signature_is_valid_default(self):
        """По умолчанию is_valid=True."""
        _, signer, _, doc = _make_signer_setup()
        sig = SignatureFactory(document=doc, user=signer, ip_address="127.0.0.1")
        assert sig.is_valid is True

    def test_signature_ip_stored(self):
        """IP-адрес сохраняется корректно."""
        _, signer, _, doc = _make_signer_setup()
        sig = SignatureFactory(document=doc, user=signer, ip_address="203.0.113.5")
        assert sig.ip_address == "203.0.113.5"
