from pydantic import ValidationError as PydanticValidationError

from django.conf import settings
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm, PasswordResetForm
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib.auth.views import PasswordResetConfirmView

from shop.models import EmailVerificationChallenge
from .rate_limits import is_rate_limited
from .schemas import (
    EmailChangeSchema,
    EmailVerificationCodeSchema,
    EmailVerificationSchema,
    ForgotPasswordSchema,
    LoginSchema,
    PasswordChangeSchema,
    PasswordResetSchema,
    ProfileUpdateSchema,
    RegistrationSchema,
    ResendVerificationSchema,
)
from .security import log_security_event
from .services import (
    ChallengeCooldown,
    ChallengeError,
    EmailAlreadyRegistered,
    EmailDeliveryError,
    create_unverified_user,
    issue_email_challenge,
    verify_email_challenge,
)


def _payload(request):
    return {
        key: value
        for key, value in request.POST.items()
        if key not in {'csrfmiddlewaretoken', 'next'}
    }


def _validate(schema, request, *, fields=None):
    try:
        payload = _payload(request)
        if fields is not None:
            payload = {key: payload.get(key, '') for key in fields}
        return schema.model_validate(payload), {}

    except PydanticValidationError as exc:
        errors = {}

        for error in exc.errors():
            field = str(error['loc'][0]) if error['loc'] else '__all__'
            errors.setdefault(field, []).append(error['msg'])

        return None, errors


def _render(request, template_name, *, errors=None, status=200, **context):
    normalized_errors = {}

    for field, messages_for_field in (errors or {}).items():
        key = 'non_field' if field == '__all__' else field
        normalized_errors[key] = list(messages_for_field)

    return render(request, template_name, {'errors': normalized_errors, **context}, status=status)


def _safe_next_url(request):
    candidate = request.POST.get('next') or request.GET.get('next')

    if candidate and url_has_allowed_host_and_scheme(candidate, allowed_hosts={request.get_host()}, require_https=not settings.DEBUG):
        return candidate

    return settings.LOGIN_REDIRECT_URL


def _throttled(request, *, scope, email, limit, window):
    if is_rate_limited(request, scope=scope, identifier=email, limit=limit, window_seconds=window):
        return _render(request, 'auth/rate_limited.html', status=429)

    return None


@require_http_methods(['GET', 'POST'])
def register(request):
    if request.user.is_authenticated:
        return redirect('shop:home')
    if request.method == 'GET':
        return _render(request, 'auth/register.html')

    payload, errors = _validate(RegistrationSchema, request)
    if errors:
        return _render(request, 'auth/register.html', errors=errors, status=400)

    if throttled := _throttled(request, scope='registration', email=payload.email, limit=5, window=3600):
        return throttled

    password = payload.password.get_secret_value()
    candidate_user = get_user_model()(email=payload.email, first_name=payload.first_name, last_name=payload.last_name)

    try:
        validate_password(password, candidate_user)
        user = create_unverified_user(
            email=payload.email,
            first_name=payload.first_name,
            last_name=payload.last_name,
            password=password,
        )

        issue_email_challenge(user=user, purpose=EmailVerificationChallenge.Purpose.REGISTRATION)

    except ValidationError as exc:
        return _render(request, 'auth/register.html', errors={'password': list(exc.messages)}, status=400)

    except EmailAlreadyRegistered:
        log_security_event('registration_existing_email', request, email=payload.email)
        messages.success(request, 'If this email can be registered, verification instructions will be sent.')

        return redirect('shop:resend_verification')

    except EmailDeliveryError:
        log_security_event('registration_email_delivery_failed', request, email=payload.email)
        messages.error(request, 'We could not send a verification code. Please use resend verification.')

        return redirect('shop:resend_verification')

    log_security_event('registration_created', request, user=user, email=user.email)
    request.session['registration_verification_email'] = user.email
    messages.success(request, 'Your account has been created successfully!')

    return redirect('shop:verify_email')


@require_http_methods(['GET', 'POST'])
def verify_email(request):
    email = request.session.get('registration_verification_email', '')

    if request.method == 'GET':
        return _render(request, 'auth/verify_email.html')

    if not email:
        messages.error(request, 'Your verification session has expired. Please request a new code.')
        return redirect('shop:resend_verification')

    payload, errors = _validate(EmailVerificationCodeSchema, request, fields={'code'})
    if errors:
        return _render(request, 'auth/verify_email.html', errors=errors, status=400)

    if throttled := _throttled(request, scope='verify-email', email=email, limit=10, window=300):
        return throttled

    try:
        user = verify_email_challenge(
            email=email,
            code=payload.code.get_secret_value(),
            purpose=EmailVerificationChallenge.Purpose.REGISTRATION,
        )

    except ChallengeError:
        log_security_event('email_verification_failed', request, email=email)
        return _render(request, 'auth/verify_email.html', errors={'code': ['The code is invalid or expired.']}, status=400)

    request.session.pop('registration_verification_email', None)
    login(request, user)
    log_security_event('email_verified', request, user=user, email=user.email)
    messages.success(request, 'Your email has been verified.')

    return redirect(_safe_next_url(request))


@require_http_methods(['GET', 'POST'])
def resend_verification(request):
    if request.method == 'GET':
        return _render(request, 'auth/resend_verification.html')

    payload, errors = _validate(ResendVerificationSchema, request)
    if errors:
        return _render(request, 'auth/resend_verification.html', errors=errors, status=400)

    if throttled := _throttled(request, scope='resend-verification', email=payload.email, limit=5, window=3600):
        return throttled

    user = get_user_model().objects.filter(email__iexact=payload.email, is_active=False).first()
    if user:
        try:
            issue_email_challenge(user=user, purpose=EmailVerificationChallenge.Purpose.REGISTRATION)
            request.session['registration_verification_email'] = user.email
            log_security_event('email_verification_resent', request, user=user, email=user.email)

        except (ChallengeCooldown, EmailDeliveryError):
            pass

    messages.success(request, 'If an account exists, a Verification Email will be sent soon')

    request.session['registration_verification_email'] = payload.email
    return redirect('shop:verify_email')


@require_http_methods(['GET', 'POST'])
def login_view(request):
    if request.user.is_authenticated:
        return redirect('shop:home')

    if request.method == 'GET':
        return _render(request, 'auth/login.html', next_url=request.GET.get('next', ''))

    payload, errors = _validate(LoginSchema, request)

    if errors:
        return _render(request, 'auth/login.html', errors=errors, next_url=request.POST.get('next', ''), status=400)
    if throttled := _throttled(request, scope='login', email=payload.email, limit=5, window=900):
        return throttled

    user = authenticate(request, email=payload.email, password=payload.password.get_secret_value())

    if user is None:
        log_security_event('login_failed', request, email=payload.email)

        return _render(
            request,
            'auth/login.html',
            errors={'__all__': ['Invalid email or password']},
            next_url=request.POST.get('next', ''),
            status=400,
        )

    login(request, user)
    log_security_event('login_succeeded', request, user=user, email=user.email)
    messages.success(request, 'You have successfully signed in')

    return redirect(_safe_next_url(request))


@require_POST
@login_required
def logout_view(request):
    user = request.user

    logout(request)
    log_security_event('logout', request, user=user, email=user.email)

    messages.success(request, 'You have been signed out')

    return redirect('shop:login')


@require_http_methods(['GET', 'POST'])
def password_reset_request(request):
    if request.method == 'GET':
        return _render(request, 'auth/password_reset.html')

    payload, errors = _validate(ForgotPasswordSchema, request)

    if errors:
        return _render(request, 'auth/password_reset.html', errors=errors, status=400)
    if throttled := _throttled(request, scope='password-reset', email=payload.email, limit=5, window=3600):
        return throttled

    form = PasswordResetForm({'email': payload.email})
    if form.is_valid():
        form.save(
            request=request,
            use_https=request.is_secure(),
            from_email=settings.DEFAULT_FROM_EMAIL,
            email_template_name='auth/password_reset_email.txt',
            subject_template_name='auth/password_reset_subject.txt',
        )

    log_security_event('password_reset_requested', request, email=payload.email)
    messages.success(request, 'If an account exists, a reset link has been sent')

    return redirect('shop:login')


@require_http_methods(['GET', 'POST'])
@login_required
def password_change(request):
    if request.method == 'GET':
        return _render(request, 'auth/password_change.html')

    payload, errors = _validate(PasswordChangeSchema, request)

    if errors:
        return _render(request, 'auth/password_change.html', errors=errors, status=400)

    form = PasswordChangeForm(
        request.user,
        {
            'old_password': payload.old_password.get_secret_value(),
            'new_password1': payload.new_password1.get_secret_value(),
            'new_password2': payload.new_password2.get_secret_value(),
        },
    )

    if not form.is_valid():
        return _render(request, 'auth/password_change.html', errors=form.errors, status=400)

    user = form.save()
    update_session_auth_hash(request, user)
    log_security_event('password_changed', request, user=user, email=user.email)
 
    messages.success(request, 'Your password has been changed')

    return redirect('shop:dashboard')


class ValidatedPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'auth/password_reset_confirm.html'
    success_url = reverse_lazy('shop:password_reset_complete')

    def post(self, request, *args, **kwargs):
        _, errors = _validate(PasswordResetSchema, request)

        if errors:
            form = self.get_form()

            for field, messages_for_field in errors.items():
                target = field if field in form.fields else None
                for message in messages_for_field:
                    form.add_error(target, message)

            return self.render_to_response(self.get_context_data(form=form), status=400)

        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)

        log_security_event('password_reset_completed', self.request, user=self.user, email=self.user.email)

        return response


@require_http_methods(['GET', 'POST'])
@login_required
def dashboard(request):
    if request.method == 'GET':
        return _render(request, 'auth/dashboard.html')

    payload, errors = _validate(ProfileUpdateSchema, request)

    if errors:
        return _render(request, 'auth/dashboard.html', errors=errors, status=400)

    if payload.phone_number:
        return _render(
            request,
            'auth/dashboard.html',
            errors={'phone_number': ['Phone numbers are collected with an address or checkout, not on the account.']},
            status=400,
        )

    request.user.first_name = payload.first_name
    request.user.last_name = payload.last_name
    request.user.save(update_fields=['first_name', 'last_name'])

    messages.success(request, 'Your profile has been updated')
    return redirect('shop:dashboard')


@require_http_methods(['GET', 'POST'])
@login_required
def account_security(request):
    if request.method == 'GET':
        return _render(request, 'auth/account_security.html')

    return _render(
        request,
        'auth/dashboard.html',
        errors={'phone_number': ['Phone numbers are collected with an address or checkout, not on the account.']},
        status=400,
        redirect="shop:account_security"
    )



@require_http_methods(['GET', 'POST'])
@login_required
def email_change(request):
    if request.method == 'GET':
        return _render(request, 'auth/email_change.html')
    payload, errors = _validate(EmailChangeSchema, request)

    if errors:
        return _render(request, 'auth/email_change.html', errors=errors, status=400)

    if not request.user.check_password(payload.current_password.get_secret_value()):
        return _render(request, 'auth/email_change.html', errors={'current_password': ['Current password is incorrect.']}, status=400)

    if payload.email == request.user.email.lower():
        return _render(request, 'auth/email_change.html', errors={'email': ['Enter a different email address.']}, status=400)

    if get_user_model().objects.filter(email__iexact=payload.email).exclude(pk=request.user.pk).exists():
        return _render(request, 'auth/email_change.html', errors={'email': ['This email address cannot be used.']}, status=400)

    if throttled := _throttled(request, scope='email-change', email=payload.email, limit=3, window=3600):
        return throttled

    try:
        issue_email_challenge(
            user=request.user,
            purpose=EmailVerificationChallenge.Purpose.EMAIL_CHANGE,
            target_email=payload.email,
        )

    except ChallengeCooldown:
        return _render(request, 'auth/email_change.html', errors={'__all__': ['Please wait before requesting another code.']}, status=429)

    except EmailDeliveryError:
        log_security_event('email_change_delivery_failed', request, user=request.user, email=payload.email)

        return _render(request, 'auth/email_change.html', errors={'__all__': ['We could not send a verification code.']}, status=503)

    log_security_event('email_change_requested', request, user=request.user, email=payload.email)

    return redirect(f"{reverse('shop:verify_email_change')}?email={payload.email}")


@require_http_methods(['GET', 'POST'])
@login_required
def verify_email_change(request):
    if request.method == 'GET':
        return _render(request, 'auth/verify_email_change.html', email=request.GET.get('email', ''))

    payload, errors = _validate(EmailVerificationSchema, request)
    if errors:
        return _render(request, 'auth/verify_email_change.html', errors=errors, status=400)

    if throttled := _throttled(request, scope='verify-email-change', email=payload.email, limit=10, window=300):
        return throttled

    try:
        user = verify_email_challenge(
            email=payload.email,
            code=payload.code.get_secret_value(),
            purpose=EmailVerificationChallenge.Purpose.EMAIL_CHANGE,
            user=request.user,
        )

    except ChallengeError:
        log_security_event('email_change_verification_failed', request, user=request.user, email=payload.email)
        return _render(request, 'auth/verify_email_change.html', errors={'code': ['The code is invalid or expired.']}, status=400)

    log_security_event('email_changed', request, user=user, email=user.email)
    messages.success(request, 'Your email address has been changed')

    return redirect('shop:dashboard')
