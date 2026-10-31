from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def refuse_unmapped_legacy_invoices(apps, schema_editor):
    LegacyInvoice = apps.get_model('shop', 'LegacyInvoice')
    if LegacyInvoice.objects.exists():
        raise RuntimeError(
            'LegacyInvoice rows exist and cannot be mapped from Customer to auth.User automatically. '
            'Map those records explicitly before applying this migration.'
        )


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0013_domain_models'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(refuse_unmapped_legacy_invoices, migrations.RunPython.noop),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        'ALTER TABLE "shop_legacyinvoice" '
                        'DROP CONSTRAINT IF EXISTS "shop_invoice_customer_id_id_a870a04a_fk_shop_customer_id"; '
                        'ALTER TABLE "shop_legacyinvoice" '
                        'RENAME COLUMN "customer_id_id" TO "user_id"; '
                        'ALTER TABLE "shop_legacyinvoice" '
                        'ADD CONSTRAINT "shop_legacyinvoice_user_id_auth_user_fk" '
                        'FOREIGN KEY ("user_id") REFERENCES "auth_user" ("id") '
                        'DEFERRABLE INITIALLY DEFERRED;'
                    ),
                    reverse_sql=(
                        'ALTER TABLE "shop_legacyinvoice" '
                        'DROP CONSTRAINT IF EXISTS "shop_legacyinvoice_user_id_auth_user_fk"; '
                        'ALTER TABLE "shop_legacyinvoice" '
                        'RENAME COLUMN "user_id" TO "customer_id_id"; '
                        'ALTER TABLE "shop_legacyinvoice" '
                        'ADD CONSTRAINT "shop_invoice_customer_id_id_a870a04a_fk_shop_customer_id" '
                        'FOREIGN KEY ("customer_id_id") REFERENCES "shop_customer" ("id") '
                        'DEFERRABLE INITIALLY DEFERRED;'
                    ),
                ),
            ],
            state_operations=[
                migrations.RenameField(
                    model_name='legacyinvoice',
                    old_name='customer_id',
                    new_name='user',
                ),
                migrations.AlterField(
                    model_name='legacyinvoice',
                    name='user',
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='legacy_invoices',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='user',
                    ),
                ),
            ],
        ),
    ]
