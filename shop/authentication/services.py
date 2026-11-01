import hashlib
import hmac
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.utils import timezone

from shop.models import EmailVerificationChallenge


OTP_EXPIRY = timedelta(minutes=5)
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_COOLDOWN = timedelta(seconds=60)


class EmailAlreadyRegistered(Exception):
    pass


class ChallengeError(Exception):
    pass


class ChallengeCooldown(ChallengeError):
    pass


class EmailDeliveryError(ChallengeError):
    pass


def otp_digest(*, user_id, purpose, code):
    message = f'{user_id}:{purpose}:{code}'.encode()
    return hmac.new(settings.EMAIL_OTP_HMAC_SECRET.encode(), message, hashlib.sha256).hexdigest()


def _new_username():
    return f'user_{secrets.token_hex(16)}'


def create_unverified_user(*, email, first_name, last_name, password):
    User = get_user_model()
    try:
        with transaction.atomic():
            if User.objects.filter(email__iexact=email).exists():
                raise EmailAlreadyRegistered
            user = User.objects.create_user(
                username=_new_username(),
                email=email,
                first_name=first_name,
                last_name=last_name,
                password=password,
                is_active=False,
            )
            return user
    except IntegrityError as exc:
        # The PostgreSQL expression index is the final authority under races.
        raise EmailAlreadyRegistered from exc


def issue_email_challenge(*, user, purpose, target_email=''):
    now = timezone.now()
    User = get_user_model()
    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=user.pk)
        recent = (
            EmailVerificationChallenge.objects.select_for_update()
            .filter(user=user, purpose=purpose, consumed_at__isnull=True)
            .order_by('-sent_at')
            .first()
        )
        if recent and now - recent.sent_at < OTP_RESEND_COOLDOWN:
            raise ChallengeCooldown

        EmailVerificationChallenge.objects.filter(
            user=user,
            purpose=purpose,
            consumed_at__isnull=True,
        ).update(consumed_at=now)
        code = f'{secrets.randbelow(1_000_000):06d}'
        challenge = EmailVerificationChallenge.objects.create(
            user=user,
            purpose=purpose,
            target_email=target_email,
            code_digest=otp_digest(user_id=user.pk, purpose=purpose, code=code),
            expires_at=now + OTP_EXPIRY,
            max_attempts=OTP_MAX_ATTEMPTS,
            sent_at=now,
        )

    recipient = target_email or user.email
    try:
        send_mail(
            subject='Your LogixShop verification code',
            message=(
                f'Your verification code is {code}. It expires in 5 minutes. '
                'If you did not request this, you can ignore this email.'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
    except Exception as exc:
        EmailVerificationChallenge.objects.filter(pk=challenge.pk, consumed_at__isnull=True).update(consumed_at=timezone.now())
        raise EmailDeliveryError from exc
    return challenge


def verify_email_challenge(*, email, code, purpose, user=None):
    User = get_user_model()
    now = timezone.now()
    invalid_code = False
    verified_user = None
    with transaction.atomic():
        if user is not None:
            try:
                user = User.objects.select_for_update().get(pk=user.pk)
            except User.DoesNotExist as exc:
                raise ChallengeError from exc
        else:
            try:
                user = User.objects.select_for_update().get(email__iexact=email)
            except User.DoesNotExist as exc:
                raise ChallengeError from exc

        challenge = (
            EmailVerificationChallenge.objects.select_for_update()
            .filter(user=user, purpose=purpose, consumed_at__isnull=True)
            .order_by('-created_at')
            .first()
        )
        if not challenge or challenge.expires_at <= now or challenge.attempts >= challenge.max_attempts:
            raise ChallengeError
        expected = otp_digest(user_id=user.pk, purpose=purpose, code=code)
        valid_target = (
            purpose != EmailVerificationChallenge.Purpose.EMAIL_CHANGE
            or challenge.target_email.lower() == email
        )
        if not valid_target or not hmac.compare_digest(challenge.code_digest, expected):
            challenge.attempts += 1
            update_fields = ['attempts']
            if challenge.attempts >= challenge.max_attempts:
                challenge.consumed_at = now
                update_fields.append('consumed_at')
            challenge.save(update_fields=update_fields)
            invalid_code = True
        else:
            challenge.consumed_at = now
            challenge.attempts += 1
            challenge.save(update_fields=['consumed_at', 'attempts'])
            if purpose == EmailVerificationChallenge.Purpose.REGISTRATION:
                if not user.is_active:
                    user.is_active = True
                    user.save(update_fields=['is_active'])
            elif purpose == EmailVerificationChallenge.Purpose.EMAIL_CHANGE:
                if not challenge.target_email:
                    raise ChallengeError
                try:
                    user.email = challenge.target_email
                    user.save(update_fields=['email'])
                except IntegrityError as exc:
                    raise ChallengeError from exc
            verified_user = user
    if invalid_code:
        raise ChallengeError
    return verified_user
