# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# GNU GPLv3 License. See license.txt


import trivena_framework as trivena

from trivena_insights.hooks import insights_path

no_cache = 1


def get_context(context):
    try:
        from trivena_framework.integrations.frappe_providers.frappecloud_billing import is_fc_site
    except ImportError:

        def is_fc_site():
            return False

    csrf_token = trivena.sessions.get_csrf_token()
    trivena.db.commit()
    context.boot = {
        "csrf_token": csrf_token,
        "site_name": trivena.local.site,
        "is_fc_site": is_fc_site(),
        "socketio_port": trivena.conf.get("socketio_port"),
        "insights_path": f"/{insights_path}",
    }
