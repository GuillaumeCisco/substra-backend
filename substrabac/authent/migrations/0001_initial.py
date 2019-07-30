# Generated by Django 2.1.2 on 2019-07-30 08:03

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ExternalAuthent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username', models.CharField(max_length=256)),
                ('password', models.CharField(max_length=256)),
            ],
        ),
        migrations.CreateModel(
            name='InternalAuthent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('modulus', models.CharField(max_length=64)),
            ],
        ),
        migrations.CreateModel(
            name='Node',
            fields=[
                ('name', models.CharField(blank=True, max_length=256, primary_key=True, serialize=False)),
            ],
        ),
        migrations.CreateModel(
            name='Permission',
            fields=[
                ('name', models.CharField(blank=True, max_length=256, primary_key=True, serialize=False)),
            ],
        ),
        migrations.AddField(
            model_name='internalauthent',
            name='permission',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='authent.Permission'),
        ),
        migrations.AddField(
            model_name='externalauthent',
            name='node',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='authent.Node'),
        ),
    ]
