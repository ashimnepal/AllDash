from django.db import migrations


CATEGORIES = ["Food", "Utilities", "Transport", "Leisure", "Subscriptions"]


def seed_categories(apps, schema_editor):
    Category = apps.get_model("nodis_app", "Category")
    for name in CATEGORIES:
        Category.objects.get_or_create(slug=name.lower(), defaults={"name": name})


def remove_categories(apps, schema_editor):
    Category = apps.get_model("nodis_app", "Category")
    Category.objects.filter(slug__in=[name.lower() for name in CATEGORIES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("nodis_app", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_categories, remove_categories),
    ]
