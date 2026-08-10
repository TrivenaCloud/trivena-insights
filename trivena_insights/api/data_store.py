import trivena_framework as trivena

from trivena_insights.decorators import insights_whitelist, validate_type
from trivena_insights.insights.doctype.insights_table_v3.insights_table_v3 import get_table_name


@insights_whitelist()
@validate_type
def get_data_store_tables(data_source: str | None = None, search_term: str | None = None, limit: int = 100):
    filters = {"stored": 1}
    if data_source:
        filters["data_source"] = data_source
    or_filters = (
        {"label": ["like", f"%{search_term}%"], "table": ["like", f"%{search_term}%"]}
        if search_term
        else None
    )
    # get_list applies get_permission_query_conditions, keeping tables scoped to the caller
    tables = trivena.get_list(
        "Insights Table v3",
        filters=filters,
        or_filters=or_filters,
        fields=["name", "table", "label", "data_source", "last_synced_on"],
        limit=limit,
    )
    database_types = {
        d.name: d.database_type
        for d in trivena.get_all(
            "Insights Data Source v3",
            filters={"name": ["in", list({t.data_source for t in tables})]},
            fields=["name", "database_type"],
        )
    }

    ret = []
    for table in tables:
        ret.append(
            trivena._dict(
                {
                    "name": table.name,
                    "label": table.label,
                    "table_name": table.table,
                    "data_source": table.data_source,
                    "database_type": database_types.get(table.data_source),
                    "last_synced_on": table.last_synced_on,
                }
            )
        )
    return ret


@insights_whitelist(role="Insights Admin")
@validate_type
def import_table(data_source: str, table_name: str):
    name = get_table_name(data_source, table_name)
    table_doc = trivena.get_doc("Insights Table v3", name)
    table_doc.import_to_warehouse()


def sync_tables():
    # called daily via hooks
    tables = trivena.get_all(
        "Insights Table v3",
        filters={"stored": 1},
        fields=["name", "data_source", "table"],
    )

    for table in tables:
        import_table(table.data_source, table.table)


def update_failed_sync_status():
    from trivena_framework.query_builder import Interval
    from trivena_framework.query_builder.functions import Now

    Log = trivena.qb.DocType("Insights Table Import Log")
    logs = trivena.db.get_values(
        Log,
        ((Log.status == "In Progress") & (Log.creation < (Now() - Interval(hours=1)))),
        pluck="name",
    )

    if not logs:
        return

    for log in logs:
        trivena.db.set_value("Insights Table Import Log", log, "status", "Failed")
