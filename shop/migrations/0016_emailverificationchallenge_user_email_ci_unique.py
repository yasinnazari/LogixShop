from django.conf import settings
from django.db import migrations, models
from django.db.models import F, Q
from django.utils import timezone
import django.db.models.deletion


def verify_existing_user_emails(apps, schema_editor):
    User = apps.get_model(*settings.AUTH_USER_MODEL.split('.'))
    duplicates = (
        User.objects.exclude(email__isnull=True)
        .exclude(email__exact='')
        .extra(select={'normalized_email': 'LOWER(TRIM(email))'})
        .values('normalized_email')
        .annotate(total=models.Count('id'))
        .filter(total__gt=1)
    )
    if duplicates.exists():
        raise RuntimeError(
            'Cannot add the case-insensitive email uniqueness constraint because duplicate non-empty emails exist. '
            'Resolve the duplicates through an approved account-mapping plan before applying this migration.'
        )


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('shop', '0015_remove_customer_state'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(verify_existing_user_emails, migrations.RunPython.noop),
        migrations.RunSQL(
            sql=(
                'CREATE UNIQUE INDEX "auth_user_email_ci_unique_not_blank" '
                'ON "auth_user" (LOWER(TRIM("email"))) '
                'WHERE TRIM("email") <> \'\';'
            ),
            reverse_sql='DROP INDEX IF EXISTS "auth_user_email_ci_unique_not_blank";',
        ),
        migrations.CreateModel(
            name='EmailVerificationChallenge',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code_digest', models.CharField(max_length=64)),
                ('purpose', models.CharField(choices=[('REGISTRATION', 'Registration'), ('EMAIL_CHANGE', 'Email change')], max_length=32)),
                ('target_email', models.EmailField(blank=True, default='', max_length=254)),
                ('expires_at', models.DateTimeField()),
                ('attempts', models.PositiveSmallIntegerField(default=0)),
                ('max_attempts', models.PositiveSmallIntegerField(default=5)),
                ('sent_at', models.DateTimeField(default=timezone.now)),
                ('consumed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='email_verification_challenges', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'indexes': [
                    models.Index(fields=['user', 'purpose', '-created_at'], name='email_challenge_user_idx'),
                    models.Index(fields=['expires_at'], name='email_challenge_expiry_idx'),
                ],
                'constraints': [
                    models.CheckConstraint(condition=Q(('max_attempts__gt', 0)), name='email_challenge_max_attempts_positive'),
                    models.CheckConstraint(condition=Q(('attempts__lte', F('max_attempts'))), name='email_challenge_attempts_valid'),
                ],
            },
        ),
    ]
