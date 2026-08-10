# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import json

import trivena_framework as trivena
from trivena_framework.utils.install import complete_setup_wizard


def before_tests():
    complete_setup_wizard()
    trivena.db.commit()


def delete_all_records():
    trivena.db.delete("Version", {"ref_doctype": ("like", "Insights%")})
    trivena.db.delete("View Log", {"reference_doctype": ("like", "Insights%")})
    for doctype in trivena.get_all("DocType", filters={"module": "Insights", "issingle": 0}, pluck="name"):
        trivena.db.delete(doctype)


def create_site_db():
    data_source_fixture_path = trivena.get_app_path("trivena_insights", "fixtures", "insights_data_source_v3.json")
    with open(data_source_fixture_path) as f:
        site_db = json.load(f)[0]
        trivena.get_doc(site_db).insert()


def create_sqlite_db():
    db = trivena.new_doc("Insights Data Source v3")
    db.title = "Test SQLite DB"
    db.database_type = "SQLite"
    db.database_name = "test_sqlite_db"
    import_todo_table(db)
    db.save()


def import_todo_table(db):
    import pandas as pd

    data = [
        [
            "name",
            "docstatus",
            "description",
            "status",
            "date",
            "owner",
            "modified_by",
            "modified",
            "creation",
        ],
        [
            0,
            0,
            "Test 1",
            "Open",
            "2021-09-01 00:00:00",
            "Administrator",
            "Administrator",
            "2021-09-01 00:00:00",
            "2021-09-01 00:00:00",
        ],
    ]
    df = pd.DataFrame(data[1:], columns=data[0])
    df.to_sql(
        name="tabToDo",
        con=db._db.engine,
        index=False,
        if_exists="replace",
    )


def create_insights_query(title=None, data_source=None):
    query = trivena.new_doc("Insights Query v3")
    query.title = title or "Test Query"
    query.data_source = data_source or "Site DB"
    query.save()
    return query
