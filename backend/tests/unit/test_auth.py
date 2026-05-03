"""
Unit tests for authentication functions (JWT, password hashing).

Tests:
- UT-1: JWT token generation and validation
- Password hashing and verification
- Token expiration handling
"""
import pytest
from datetime import timedelta, datetime, timezone
from jose import jwt, JWTError

from app.auth.security import (
    hash_password,
    verify_password,
    create_access_token,
    verify_token,
    SECRET_KEY,
    ALGORITHM,
)


@pytest.mark.unit
class TestPasswordHashing:
    """Test password hashing and verification"""

    def test_hash_password_creates_valid_hash(self):
        """Test that password hashing produces a non-empty hash"""
        password = "test_password_123"
        hashed = hash_password(password)
        
        assert hashed is not None
        assert len(hashed) > 0
        assert hashed != password  # Hash should be different from plaintext

    def test_verify_password_accepts_correct_password(self):
        """Test that correct password verification returns True"""
        password = "my_secure_password"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True

    def test_verify_password_rejects_incorrect_password(self):
        """Test that incorrect password verification returns False"""
        password = "correct_password"
        wrong_password = "wrong_password"
        hashed = hash_password(password)
        
        assert verify_password(wrong_password, hashed) is False

    def test_hash_password_produces_different_hashes_for_same_input(self):
        """Test that hashing same password twice produces different hashes (salted)"""
        password = "same_password"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        # Hashes should be different due to random salt
        assert hash1 != hash2
        # But both should verify correctly
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)


@pytest.mark.unit
class TestJWTTokenGeneration:
    """Test JWT token creation and verification - UT-1"""

    def test_create_access_token_returns_valid_jwt(self):
        """UT-1: Test JWT token generation returns valid token string"""
        data = {"sub": "testuser", "role": "admin"}
        token = create_access_token(data)
        
        # Token should be a non-empty string
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Token should have 3 parts (header.payload.signature)
        parts = token.split(".")
        assert len(parts) == 3

    def test_create_access_token_includes_payload_data(self):
        """Test that JWT token includes the provided data"""
        data = {"sub": "admin", "role": "admin", "custom": "value"}
        token = create_access_token(data)
        
        # Decode without verification to inspect payload
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        assert decoded["sub"] == "admin"
        assert decoded["role"] == "admin"
        assert decoded["custom"] == "value"
        assert "exp" in decoded  # Expiration should be auto-added

    def test_create_access_token_includes_expiration(self):
        """Test that JWT token includes expiration time"""
        data = {"sub": "testuser"}
        token = create_access_token(data)
        
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        assert "exp" in decoded
        exp_time = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        
        # Expiration should be in the future (default 30 minutes)
        assert exp_time > now
        assert (exp_time - now).total_seconds() > 0

    def test_create_access_token_custom_expiration(self):
        """Test JWT token creation with custom expiration delta"""
        data = {"sub": "testuser"}
        custom_expire = timedelta(minutes=60)
        token = create_access_token(data, expires_delta=custom_expire)
        
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp_time = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        
        # Should expire in approximately 60 minutes
        delta_seconds = (exp_time - now).total_seconds()
        assert 3500 < delta_seconds < 3700  # Allow 100s tolerance

    def test_verify_token_accepts_valid_token(self):
        """Test that verify_token successfully decodes valid JWT"""
        data = {"sub": "admin", "role": "admin"}
        token = create_access_token(data)
        
        payload = verify_token(token)
        
        assert payload["sub"] == "admin"
        assert payload["role"] == "admin"
        assert "exp" in payload

    def test_verify_token_rejects_invalid_token(self):
        """Test that verify_token raises HTTPException for invalid token"""
        invalid_token = "invalid.jwt.token"
        
        with pytest.raises(Exception):  # Should raise HTTPException or JWTError
            verify_token(invalid_token)

    def test_verify_token_rejects_expired_token(self):
        """Test that expired token is rejected"""
        data = {"sub": "testuser"}
        # Create token that expires immediately
        token = create_access_token(data, expires_delta=timedelta(seconds=-1))
        
        with pytest.raises(Exception):  # Should raise due to expiration
            verify_token(token)

    def test_verify_token_rejects_tampered_token(self):
        """Test that tampered token is rejected"""
        data = {"sub": "admin", "role": "admin"}
        token = create_access_token(data)
        
        # Tamper with the token by modifying a character
        tampered_token = token[:-10] + "X" + token[-9:]
        
        with pytest.raises(Exception):  # Should raise due to invalid signature
            verify_token(tampered_token)
