import hashlib

from django.core.cache import cache


def client_ip(request):
    # Do not trust X-Forwarded-For unless a deployment-specific trusted-proxy layer
    # has already replaced REMOTE_ADDR.
    return request.META.get('REMOTE_ADDR', 'unknown')


def is_rate_limited(request, *, scope, identifier, limit, window_seconds):
    """Return True once either the IP or normalized account bucket exceeds its limit."""
    buckets = (f'ip:{client_ip(request)}', f'account:{identifier.lower()}')
    limited = False
    for bucket in buckets:
        digest = hashlib.sha256(f'{scope}:{bucket}'.encode()).hexdigest()
        key = f'auth-rate-limit:{scope}:{digest}'
        if cache.add(key, 1, timeout=window_seconds):
            continue
        try:
            count = cache.incr(key)
        except ValueError:
            # A concurrent expiry is harmless; retry on the next request.
            cache.add(key, 1, timeout=window_seconds)
            continue
        limited = limited or count > limit
    return limited
