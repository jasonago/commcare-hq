# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

from corehq.form_processor.models import CaseTransaction
from corehq.sql_db.operations import RawSQLMigration, HqRunSQL

migrator = RawSQLMigration(('corehq', 'sql_accessors', 'sql_templates'), {
    'TRANSACTION_TYPE_FORM': CaseTransaction.TYPE_FORM
})


class Migration(migrations.Migration):

    dependencies = [
        ('sql_accessors', '0028_rename_get_multiple_forms_attachments'),
    ]

    operations = [
        HqRunSQL(
            "DROP FUNCTION IF EXISTS get_case_ids_in_domain(TEXT, TEXT)",
            "SELECT 1"
        ),
        migrator.get_migration('get_case_ids_in_domain_1.sql'),
        HqRunSQL(
            "DROP FUNCTION IF EXISTS get_case_ids_in_domain_by_owners(text, text[], boolean)",
            "SELECT 1"
        )
    ]