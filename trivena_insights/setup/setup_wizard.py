# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import os

import trivena_framework as trivena

from trivena_insights.decorators import insights_whitelist
from trivena_insights.setup.demo import DemoDataFactory


@insights_whitelist(role="Insights Admin")
def check_demo_data_exists() -> bool:
    from trivena_insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import (
        db_connections,
    )

    if not trivena.db.exists("Insights Data Source v3", "demo_data", cache=True):
        return False

    with db_connections():
        factory = DemoDataFactory()
        factory.initialize()
        return factory.demo_data_exists()


@insights_whitelist(role="Insights Admin")
def setup_demo_data():
    if trivena.flags.in_test or os.environ.get("CI"):
        return

    try:
        factory = DemoDataFactory()
        factory.run()
        trivena.db.commit()
    except Exception:
        trivena.log_error("Insights: Demo Data Setup Failed")
        trivena.throw("Failed to setup demo data")
