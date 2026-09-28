import os
import sys
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.db.database import SessionLocal
from app.models.user import User
from app.services.identity.base import IdentityProvider, UserIdentity
from app.services.identity.local_provider import LocalIdentityProvider
from app.services.identity.ldap_provider import LDAPIdentityProvider, sanitize_ldap_input
from app.services.identity import get_identity_provider

client = TestClient(app)


# -----------------------------------------------------------------------------
# 1. Interface and Factory Tests
# -----------------------------------------------------------------------------
def test_identity_provider_subclass_contract():
    """Verify Local and LDAP providers conform to IdentityProvider contract."""
    local_prov = LocalIdentityProvider()
    ldap_prov = LDAPIdentityProvider(config_override={"LDAP_SERVER_URL": "ldap://localhost", "LDAP_BASE_DN": "dc=test,dc=org"})

    assert isinstance(local_prov, IdentityProvider)
    assert isinstance(ldap_prov, IdentityProvider)
    assert local_prov.name == "local"
    assert ldap_prov.name == "ldap"


def test_factory_invalid_provider_fails_fast():
    """Verify unknown or invalid identity provider raises ValueError without silent fallback."""
    with pytest.raises(ValueError) as exc:
        get_identity_provider("unsupported_custom_provider")
    assert "Invalid IDENTITY_PROVIDER 'unsupported_custom_provider'" in str(exc.value)


def test_factory_resolves_local():
    """Verify factory returns LocalIdentityProvider when 'local' is requested."""
    prov = get_identity_provider("local")
    assert isinstance(prov, LocalIdentityProvider)
    assert prov.name == "local"


# -----------------------------------------------------------------------------
# 2. Local Identity Provider Tests
# -----------------------------------------------------------------------------
def test_local_provider_authentication_success():
    """Verify local provider successfully authenticates valid database user."""
    db = SessionLocal()
    try:
        prov = LocalIdentityProvider()
        identity = prov.authenticate("hq_officer", "Admin123!", db)
        assert identity is not None
        assert identity.username == "hq_officer"
        assert identity.is_active is True
        assert "CMPDI_HQ_OFFICER" in identity.roles
        assert identity.auth_provider == "local"
    finally:
        db.close()


def test_local_provider_authentication_failure():
    """Verify local provider returns None for invalid password and nonexistent user."""
    db = SessionLocal()
    try:
        prov = LocalIdentityProvider()
        # Invalid password
        assert prov.authenticate("hq_officer", "WrongPassword999!", db) is None
        # Nonexistent user
        assert prov.authenticate("nonexistent_user_xyz", "AnyPassword!", db) is None
        # Empty credentials
        assert prov.authenticate("", "", db) is None
    finally:
        db.close()


def test_local_provider_disabled_user():
    """Verify local provider flags inactive/disabled users."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "hq_officer").first()
        assert user is not None
        original_state = user.is_active

        # Temporarily deactivate
        user.is_active = False
        db.commit()

        prov = LocalIdentityProvider()
        # Inactive user with correct password should return None in auth route or identity.is_active=False
        identity = prov.authenticate("hq_officer", "Admin123!", db)
        assert identity is not None
        assert identity.is_active is False

        # Restore
        user.is_active = original_state
        db.commit()
    finally:
        db.close()


def test_api_login_via_identity_abstraction():
    """Verify FastAPI /login endpoint functions seamlessly with IdentityProvider."""
    res = client.post("/api/v1/auth/login", data={"username": "hq_officer", "password": "Admin123!"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "hq_officer"
    assert data["user"]["role"] == "CMPDI_HQ_OFFICER"


# -----------------------------------------------------------------------------
# 3. LDAP / Active Directory Provider Tests
# -----------------------------------------------------------------------------
def test_ldap_provider_configuration_validation():
    """Verify LDAP provider fails fast when required configuration is missing."""
    # Missing server URL
    prov_no_url = LDAPIdentityProvider(config_override={"LDAP_BASE_DN": "dc=test,dc=org"})
    with pytest.raises(ValueError) as exc1:
        prov_no_url.validate_configuration()
    assert "LDAP_SERVER_URL is required" in str(exc1.value)

    # Missing Base DN
    prov_no_dn = LDAPIdentityProvider(config_override={"LDAP_SERVER_URL": "ldap://localhost"})
    with pytest.raises(ValueError) as exc2:
        prov_no_dn.validate_configuration()
    assert "LDAP_BASE_DN is required" in str(exc2.value)


def test_ldap_input_sanitization():
    """Verify LDAP input sanitization neutralizes special characters (RFC 4515)."""
    assert sanitize_ldap_input("admin*(|(mail=*))") == r"admin\2a\28|\28mail=\2a\29\29"
    assert sanitize_ldap_input("user\\name\x00") == r"user\5cname\00"
    assert sanitize_ldap_input("clean_user_123") == "clean_user_123"


def test_ldap_group_role_mapping():
    """Verify LDAP/AD groups map deterministically to Koyla roles."""
    group_map = {
        "CN=Koyla_HQ_Admins,OU=Groups,DC=example,DC=org": "SYSTEM_ADMIN",
        "CN=Koyla_Reviewers,OU=Groups,DC=example,DC=org": "CENTRAL_REVIEWER",
        "Koyla_Subsidiary_Users": "SUBSIDIARY_ANALYST"
    }

    prov = LDAPIdentityProvider(config_override={
        "LDAP_SERVER_URL": "ldap://internal.ad:389",
        "LDAP_BASE_DN": "dc=example,dc=org",
        "LDAP_GROUP_ROLE_MAPPING": group_map,
        "LDAP_DEFAULT_ROLE": "SUBSIDIARY_ANALYST"
    })

    identity = UserIdentity(
        id="test-id",
        username="ldap_user",
        full_name="LDAP Test User",
        roles=[],
        auth_provider="ldap",
        raw_attributes={"memberOf": [
            "CN=Koyla_HQ_Admins,OU=Groups,DC=example,DC=org",
            "CN=General_Staff,OU=Groups,DC=example,DC=org"
        ]}
    )

    resolved = prov.resolve_roles(identity)
    assert "SYSTEM_ADMIN" in resolved
    assert "CENTRAL_REVIEWER" not in resolved

    # Fallback to default role when no groups match
    unmapped_identity = UserIdentity(
        id="test-id-2",
        username="unmapped_user",
        full_name="Unmapped User",
        roles=[],
        auth_provider="ldap",
        raw_attributes={"memberOf": ["CN=Other_Group,DC=example,DC=org"]}
    )
    unmapped_resolved = prov.resolve_roles(unmapped_identity)
    assert unmapped_resolved == ["SUBSIDIARY_ANALYST"]


def test_ldap_provider_authentication_mock():
    """Verify LDAP authentication workflow using mock driver."""
    db = SessionLocal()
    try:
        class MockLDAPDriver:
            def authenticate(self, username, password, provider):
                if username == "ad_officer" and password == "SecretADPass123!":
                    return UserIdentity(
                        id="ad-user-uuid-123",
                        username="ad_officer",
                        full_name="Active Directory Officer",
                        email="ad_officer@cmpdi.internal",
                        roles=["CMPDI_HQ_OFFICER"],
                        is_active=True,
                        auth_provider="ldap"
                    )
                elif username == "disabled_officer" and password == "SecretPass!":
                    return UserIdentity(
                        id="ad-user-uuid-456",
                        username="disabled_officer",
                        full_name="Disabled AD Officer",
                        email="disabled@cmpdi.internal",
                        roles=["SUBSIDIARY_ANALYST"],
                        is_active=False,
                        auth_provider="ldap"
                    )
                return None

        prov = LDAPIdentityProvider(
            config_override={
                "LDAP_SERVER_URL": "ldap://ad.internal:389",
                "LDAP_BASE_DN": "dc=internal,dc=org"
            },
            driver=MockLDAPDriver()
        )

        # Successful auth
        res_ok = prov.authenticate("ad_officer", "SecretADPass123!", db)
        assert res_ok is not None
        assert res_ok.username == "ad_officer"
        assert res_ok.is_active is True
        assert res_ok.auth_provider == "ldap"

        # Invalid password
        res_fail = prov.authenticate("ad_officer", "WrongPassword", db)
        assert res_fail is None

        # Disabled user
        res_disabled = prov.authenticate("disabled_officer", "SecretPass!", db)
        assert res_disabled is not None
        assert res_disabled.is_active is False
    finally:
        db.close()


def test_system_health_telemetry_includes_identity_provider():
    """Verify /system/health exposes genuine identity provider telemetry."""
    res = client.get("/api/v1/system/health")
    assert res.status_code == 200
    data = res.json()
    assert "identity_provider" in data["services"]
    assert data["services"]["identity_provider"] == "UP"
    assert data.get("identity_provider_type") == "local"
