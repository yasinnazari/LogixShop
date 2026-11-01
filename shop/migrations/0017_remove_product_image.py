from django.db import migrations, models
import django.db.models.deletion


def migrate_legacy_product_images(apps, schema_editor):
    Product = apps.get_model('shop', 'Product')
    ProductImage = apps.get_model('shop', 'ProductImage')

    for product in Product.objects.all().iterator():
        if not product.image:
            raise RuntimeError(
                f'Product {product.pk} has no legacy image and cannot be migrated safely. '
                'Resolve the missing image before removing Product.image.'
            )

        primary = ProductImage.objects.filter(product_id=product.pk, is_primary=True).first()
        if primary is None:
            ProductImage.objects.create(
                product_id=product.pk,
                image=product.image.name,
                alt_text=product.title,
                sort_order=0,
                is_primary=True,
            )
        elif primary.image.name != product.image.name:
            # Product.image was the legacy source of truth. Preserve its latest
            # value in the new primary-image record before removing the column.
            primary.image = product.image.name
            primary.alt_text = primary.alt_text or product.title
            primary.save(update_fields=['image', 'alt_text'])


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0016_emailverificationchallenge_user_email_ci_unique'),
    ]

    operations = [
        migrations.RunPython(migrate_legacy_product_images, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='product',
            name='image',
        ),
    ]
