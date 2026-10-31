from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0014_legacyinvoice_user_fk'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name='Customer'),
            ],
            database_operations=[],
        ),
        migrations.AlterField(
            model_name='product',
            name='status',
            field=models.CharField(
                choices=[
                    ('DRAFT', 'Draft'),
                    ('PUBLISHED', 'Published'),
                    ('ARCHIVED', 'Archived'),
                ],
                default='DRAFT',
                max_length=20,
            ),
        ),
    ]
