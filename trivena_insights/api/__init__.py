# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import os

import trivena_framework as trivena
from trivena_framework.handler import is_valid_http_method, is_whitelisted
from trivena_framework.monitor import add_data_to_monitor

from trivena_insights.api.shared import is_public
from trivena_insights.decorators import insights_whitelist, validate_type
from trivena_insights.insights.doctype.insights_data_source_v3.ibis_utils import (
    get_columns_from_schema,
)
from trivena_insights.insights.doctype.insights_table_v3.insights_table_v3 import (
    InsightsTablev3,
)
from trivena_insights.insights.doctype.insights_team.insights_team import (
    check_data_source_permission,
)
from trivena_insights.utils import get_owned_file


@insights_whitelist()
def get_app_version():
    return trivena.get_attr("trivena_insights" + ".__version__")


@insights_whitelist()
def get_user_info():
    roles = trivena.get_roles()
    is_user = "Insights User" in roles
    is_admin = "Insights Admin" in roles

    user = trivena.db.get_value(
        "User", trivena.session.user, ["first_name", "last_name", "user_type", "language"], as_dict=1
    )

    locale = user.get("language") or trivena.db.get_single_value("System Settings", "language") or "en"

    has_demo_data = False
    if is_admin:
        from trivena_insights.setup.setup_wizard import check_demo_data_exists

        has_demo_data = check_demo_data_exists()

    return {
        "email": trivena.session.user,
        "first_name": user.get("first_name"),
        "last_name": user.get("last_name"),
        "is_admin": is_admin,
        "is_user": is_user or trivena.session.user == "Administrator",
        "can_download": is_admin or bool(trivena.db.get_single_value("Insights Settings", "allow_download")),
        # TODO: move to `get_session_info` since not user specific
        "country": trivena.db.get_single_value("System Settings", "country"),
        "locale": locale,
        "has_desk_access": user.get("user_type") == "System User",
        "has_demo_data": has_demo_data,
        "fiscal_year_start": trivena.db.get_single_value("Insights Settings", "fiscal_year_start")
        or "01-04-2020",
    }


def get_csv_file(filename: str):
    file = get_owned_file(filename)
    file_name = file.file_name or ""
    parts = file.get_extension()
    extension = parts[-1] if parts else ""
    extension = extension.lstrip(".")

    if not extension or extension not in ["csv", "xlsx", "json", "jsonl"]:
        trivena.throw(
            f"Only CSV, XLSX, JSON, and JSONL files are supported. Detected extension: '{extension}' from filename: '{file_name}'"
        )
    return file, extension


def create_uploads_if_not_exists():
    if not trivena.db.exists("Insights Data Source v3", "uploads"):
        uploads = trivena.new_doc("Insights Data Source v3")
        uploads.name = "uploads"
        uploads.title = "Uploads"
        uploads.database_type = "DuckDB"
        uploads.database_name = "insights_file_uploads"
        uploads.owner = "Administrator"
        uploads.status = "Active"
        uploads.insert(ignore_permissions=True)


@insights_whitelist()
@validate_type
def get_file_data(filename: str):
    check_data_source_permission("uploads")

    file, ext = get_csv_file(filename)
    file_path = os.path.realpath(file.get_full_path())
    file_name = file.file_name.split(".")[0]
    file_name = trivena.scrub(file_name)

    create_uploads_if_not_exists()
    ds = trivena.get_doc("Insights Data Source v3", "uploads")
    with ds.write_connection() as db:
        try:
            table = _read_uploaded_table(db, file_path, ext)
            columns = get_columns_from_schema(table.schema())
            rows = table.head(50).execute().fillna("").to_dict(orient="records")
            row_count = table.count().execute()

            return {
                "tablename": file_name,
                "rows": rows,
                "columns": columns,
                "total_rows": int(row_count),
            }
        except trivena.ValidationError:
            raise
        except Exception as e:
            trivena.log_error(e)
            raise


@insights_whitelist()
@validate_type
def import_csv_data(filename: str, tablename: str = ""):
    check_data_source_permission("uploads")

    file, ext = get_csv_file(filename)
    file_path = os.path.realpath(file.get_full_path())
    table_name = trivena.scrub(tablename) if tablename else trivena.scrub(file.file_name.split(".")[0])

    create_uploads_if_not_exists()
    ds = trivena.get_doc("Insights Data Source v3", "uploads")
    with ds.write_connection() as db:
        try:
            table = _read_uploaded_table(db, file_path, ext)
            db.create_table(table_name, table, overwrite=True)
        except trivena.ValidationError:
            raise
        except Exception as e:
            trivena.log_error(e)
            trivena.throw("Failed to import uploaded file data into Insights uploads table. Please try again.")

    InsightsTablev3.bulk_create(ds.name, [table_name])


def _read_uploaded_table(db, file_path: str, ext: str):
    try:
        if ext == "xlsx":
            return db.read_xlsx(file_path)

        if ext in ["json", "jsonl"]:
            return db.read_json(file_path)

        return db.read_csv(file_path)

    except Exception as e:
        trivena.log_error(e)

        if ext == "xlsx":
            trivena.throw(
                "Failed to read Excel data from uploaded file. Please ensure the file is a valid Excel format and try again."
            )

        if ext in ["json", "jsonl"]:
            trivena.throw(
                "Failed to read JSON data from uploaded file. Please ensure the file is a valid JSON or JSONL format and try again."
            )

        trivena.throw("Failed to read CSV data from uploaded file. Please try again.")


@trivena.whitelist(allow_guest=True)
@validate_type
def get_doc(doctype: str, name: str | int):
    try:
        from trivena_framework.client import get as _get_doc

        return _get_doc(doctype, name)
    except trivena.PermissionError:
        if not is_public(doctype, name):
            raise
        return trivena.get_doc(doctype, name).as_dict()


def _execute_doc_method(doc, method: str, args: dict | None = None, ignore_permissions=False):
    args = trivena.parse_json(args)
    method_obj = getattr(doc, method)
    fn = getattr(method_obj, "__func__", method_obj)

    if not ignore_permissions:
        doc.check_permission("read")
        is_whitelisted(fn)
        is_valid_http_method(fn)

    new_kwargs = trivena.get_newargs(fn, args or {})
    response = doc.run_method(method, **new_kwargs)
    trivena.response.docs.append(doc)
    trivena.response["message"] = response
    add_data_to_monitor(methodname=method)
    return response


@trivena.whitelist(allow_guest=True)
def run_doc_method(method: str, docs: dict | str, args: dict | None = None):
    doc = trivena.parse_json(docs)
    doctype = doc.get("doctype")
    name = doc.get("name")

    if not doctype or not name:
        raise trivena.ValidationError("Invalid document")

    try:
        docs = trivena.parse_json(docs)
        doc = trivena.get_doc(docs)
        return _execute_doc_method(doc, method, args)

    except trivena.PermissionError:
        if not is_public(doctype, name):
            raise trivena.PermissionError("You don't have permission to access this document")
        if not is_public_method(doctype, method):
            raise trivena.PermissionError("You don't have permission to access this method")

        doc = trivena.get_doc(doctype, name)
        trivena.flags.insights_for_public_access = True
        try:
            return _execute_doc_method(doc, method, args, ignore_permissions=True)
        finally:
            trivena.flags.insights_for_public_access = False


def is_public_method(doctype: str, method: str):
    public_methods = {
        "Insights Query v3": ["execute", "download_results"],
        "Insights Dashboard v3": ["get_distinct_column_values", "track_view"],
    }

    if doctype in public_methods and method in public_methods[doctype]:
        return True

    return False
