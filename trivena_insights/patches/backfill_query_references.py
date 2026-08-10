# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


def execute():
    """Populate Insights Query Reference for all existing Insights Query v3 docs."""
    import trivena_framework as trivena

    from trivena_insights.insights.query_utils import sync_query_references

    queries = trivena.get_all("Insights Query v3", fields=["name", "operations"])
    for q in queries:
        sync_query_references(q.name, q.operations)

    trivena.db.commit()
