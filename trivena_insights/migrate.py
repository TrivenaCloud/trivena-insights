# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import trivena_framework as trivena


def after_migrate():
    try:
        create_admin_team()
    except Exception:
        trivena.log_error(title="Error creating Admin Team")

    try:
        from trivena_insights.api.templates import sync_workbook_template_updates

        sync_workbook_template_updates()
    except Exception:
        trivena.log_error(title="Error syncing workbook template updates")


def create_admin_team():
    if not trivena.db.exists("Insights Team", "Admin"):
        trivena.get_doc(
            {
                "doctype": "Insights Team",
                "team_name": "Admin",
                "team_members": [{"user": "Administrator"}],
            }
        ).insert(ignore_permissions=True)
