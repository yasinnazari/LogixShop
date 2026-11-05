import hashlib
import logging
from .rate_limits import client_ip

security_logger = logging.getLogger('shop.security')

def log_security_event(event, request, *, user=None, email=None, level=logging.INFO):
    """Log auditable metadata without credentials, codes, sessions, or tokens."""

    email_fingerprint = None
    if email:
        email_fingerprint = hashlib.sha256(email.lower().encode()).hexdigest()[:16]

    security_logger.log(
        level,
        'security_event=%s user_id=%s email_fingerprint=%s ip=%s',
        event,
        getattr(user, 'pk', None),
        email_fingerprint,
        client_ip(request),
    )
