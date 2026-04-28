# Security Checklist

## Required for production

- Set non-default `DJANGO_SECRET_KEY`.
- Set strict `DJANGO_ALLOWED_HOSTS`.
- Keep `DJANGO_ENV=prod`.
- Use HTTPS at ingress/load balancer.
- Keep `POSTGRES_PASSWORD` strong and rotated.
- Set `SENTRY_DSN` for error visibility.

## Runtime controls

- CSRF enabled for state-changing endpoints.
- Secure cookies in prod (`SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`).
- HSTS enabled in prod settings.
- Request IDs in logs for tracing.

## Recommended next hardening

- Add endpoint rate limiting (`nginx` or Django level).
- Add secret scanning in CI.
- Add dependency pinning with periodic updates.
