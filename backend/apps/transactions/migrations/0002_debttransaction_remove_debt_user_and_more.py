# Generated by Django 5.0.3 on 2025-06-17 11:53

import django.db.models.deletion
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('categories', '0001_initial'),
        ('sources', '0001_initial'),
        ('transactions', '0001_initial'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='DebtTransaction',
            fields=[
                ('transaction_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='transactions.transaction')),
                ('due_date', models.DateTimeField(blank=True, null=True, verbose_name='Дата погашения')),
                ('paid_amount', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=15, verbose_name='Выплаченная сумма')),
                ('status', models.CharField(choices=[('open', 'Открыт'), ('partial', 'Частично погашен'), ('closed', 'Закрыт'), ('overdue', 'Просрочен')], default='open', max_length=10, verbose_name='Статус долга')),
                ('debtor_name', models.CharField(max_length=100, verbose_name='Имя должника/кредитора')),
                ('debt_direction', models.CharField(choices=[('from_me', 'Я дал в долг'), ('to_me', 'Мне дали в долг')], max_length=10, verbose_name='Направление долга')),
            ],
            options={
                'verbose_name': 'Долговая транзакция',
                'verbose_name_plural': 'Долговые транзакции',
            },
            bases=('transactions.transaction',),
        ),
        migrations.RemoveField(
            model_name='debt',
            name='user',
        ),
        migrations.AddField(
            model_name='transaction',
            name='is_closed',
            field=models.BooleanField(default=False, verbose_name='Закрыто'),
        ),
        migrations.AddField(
            model_name='transaction',
            name='related_user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='related_transactions', to='users.user', verbose_name='Связанный пользователь'),
        ),
        migrations.AddField(
            model_name='transaction',
            name='source',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='sources.source', verbose_name='Источник'),
        ),
        migrations.AddField(
            model_name='transaction',
            name='telegram_notified',
            field=models.BooleanField(default=False, verbose_name='Уведомление отправлено'),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='categories.category', verbose_name='Категория'),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='type',
            field=models.CharField(choices=[('income', 'Доход'), ('expense', 'Расход'), ('debt', 'Долг'), ('transfer', 'Перевод')], max_length=10, verbose_name='Тип операции'),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='users.user', verbose_name='Пользователь'),
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['user', 'is_closed'], name='transaction_user_id_dc0f22_idx'),
        ),
        migrations.AddIndex(
            model_name='debttransaction',
            index=models.Index(fields=['status'], name='transaction_status_f3ec58_idx'),
        ),
        migrations.AddIndex(
            model_name='debttransaction',
            index=models.Index(fields=['due_date'], name='transaction_due_dat_bed544_idx'),
        ),
        migrations.AddIndex(
            model_name='debttransaction',
            index=models.Index(fields=['debt_direction'], name='transaction_debt_di_dd3a82_idx'),
        ),
        migrations.DeleteModel(
            name='Debt',
        ),
    ]
