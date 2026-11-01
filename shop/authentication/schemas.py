import re

from django.core.validators import validate_email
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


PHONE_PATTERN = re.compile(r'^\+?[1-9]\d{6,14}$')


class InputSchema(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class EmailSchema(InputSchema):
    email: str = Field(min_length=3, max_length=254)

    @field_validator('email')
    @classmethod
    def normalize_and_validate_email(cls, value):
        normalized = value.strip().lower()
        validate_email(normalized)
        return normalized


class RegistrationSchema(EmailSchema):
    first_name: str = Field(min_length=1, max_length=150)
    last_name: str = Field(min_length=1, max_length=150)
    password: SecretStr = Field(min_length=12, max_length=128)
    password_confirmation: SecretStr = Field(min_length=12, max_length=128)

    @field_validator('first_name', 'last_name')
    @classmethod
    def names_must_not_be_blank(cls, value):
        if not value:
            raise ValueError('This field is required.')
        return value

    @field_validator('password_confirmation')
    @classmethod
    def passwords_must_match(cls, value, info):
        password = info.data.get('password')
        if password is not None and password.get_secret_value() != value.get_secret_value():
            raise ValueError('Passwords do not match.')
        return value


class LoginSchema(EmailSchema):
    password: SecretStr = Field(min_length=1, max_length=128)


class EmailVerificationSchema(EmailSchema):
    code: SecretStr = Field(min_length=6, max_length=6)

    @field_validator('code')
    @classmethod
    def code_must_be_six_digits(cls, value):
        if not value.get_secret_value().isdigit():
            raise ValueError('Enter the six-digit verification code.')
        return value


class ResendVerificationSchema(EmailSchema):
    pass


class ForgotPasswordSchema(EmailSchema):
    pass


class PasswordResetSchema(InputSchema):
    new_password1: SecretStr = Field(min_length=12, max_length=128)
    new_password2: SecretStr = Field(min_length=12, max_length=128)

    @field_validator('new_password2')
    @classmethod
    def passwords_must_match(cls, value, info):
        password = info.data.get('new_password1')
        if password is not None and password.get_secret_value() != value.get_secret_value():
            raise ValueError('Passwords do not match.')
        return value


class PasswordChangeSchema(PasswordResetSchema):
    old_password: SecretStr = Field(min_length=1, max_length=128)


class ProfileUpdateSchema(InputSchema):
    first_name: str = Field(min_length=1, max_length=150)
    last_name: str = Field(min_length=1, max_length=150)
    phone_number: str | None = Field(default=None, max_length=32)

    @field_validator('phone_number')
    @classmethod
    def validate_phone_if_present(cls, value):
        if value in (None, ''):
            return None
        if not PHONE_PATTERN.fullmatch(value):
            raise ValueError('Enter a valid international phone number.')
        return value


class EmailChangeSchema(EmailSchema):
    current_password: SecretStr = Field(min_length=1, max_length=128)
