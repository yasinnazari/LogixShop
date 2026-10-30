from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0011_category_slug_alter_category_title_and_more'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Invoice',
            new_name='LegacyInvoice',
        ),
        migrations.AlterField(
            model_name='legacyinvoice',
            name='customer_id',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to='shop.customer',
                verbose_name='customer_id',
            ),
        ),
        migrations.AlterField(
            model_name='legacyinvoice',
            name='product_id',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to='shop.product',
                verbose_name='product_id',
            ),
        ),
    ]
