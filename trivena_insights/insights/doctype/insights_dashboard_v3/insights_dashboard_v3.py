# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import re
from contextlib import contextmanager

import trivena_framework as trivena
import requests
from trivena_framework.model.document import Document
from trivena_framework.query_builder import Interval
from trivena_framework.query_builder.functions import Now
from trivena_framework.utils.telemetry import capture

from trivena_insights.utils import DocShare, File, get_app_url


class InsightsDashboardv3(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from trivena_framework.types import DF

        from trivena_insights.insights.doctype.insights_dashboard_chart_v3.insights_dashboard_chart_v3 import (
            InsightsDashboardChartv3,
        )

        is_public: DF.Check
        items: DF.JSON | None
        linked_charts: DF.TableMultiSelect[InsightsDashboardChartv3]
        old_name: DF.Data | None
        preview_image: DF.Data | None
        share_link: DF.Data | None
        title: DF.Data | None
        vertical_compact_layout: DF.Check
        workbook: DF.Link
    # end: auto-generated types

    @trivena.whitelist()
    def track_view(self):
        view_log = trivena.qb.DocType("View Log")
        last_viewed_recently = trivena.db.get_value(
            view_log,
            filters=(
                (view_log.creation > (Now() - Interval(minutes=5)))
                & (view_log.reference_doctype == self.doctype)
                & (view_log.reference_name == self.name)
                & (view_log.viewed_by == trivena.session.user)
            ),
            pluck="name",
        )
        if not last_viewed_recently:
            self.add_viewed(force=True)

    def get_valid_dict(self, *args, **kwargs):
        if isinstance(self.items, list):
            self.items = trivena.as_json(self.items)
        return super().get_valid_dict(*args, **kwargs)

    def as_dict(self, *args, **kwargs):
        d = super().as_dict(*args, **kwargs)

        d.read_only = not self.has_permission("write")
        if not d.read_only:
            access = self.get_acess_data()
            d.people_with_access = access[0]
            d.is_shared_with_organization = access[1]
        d.has_workbook_access = trivena.has_permission("Insights Workbook", ptype="read", doc=self.workbook)
        return d

    def after_insert(self):
        # A dashboard created already populated (e.g. imported from a template) is
        # never saved again, so before_save's diff-based preview never runs and it
        # lands without a preview. Generate the initial one here when it has content.
        if trivena.flags.in_patch or not trivena.parse_json(self.items):
            return
        trivena.enqueue_doc(
            doctype=self.doctype,
            name=self.name,
            method="generate_dashboard_preview",
            enqueue_after_commit=True,
        )

    def before_save(self):
        self.set_linked_charts()
        self.enqueue_update_dashboard_preview()

    def set_linked_charts(self):
        self.set(
            "linked_charts",
            [{"chart": item["chart"]} for item in trivena.parse_json(self.items) if item["type"] == "chart"],
        )

    @trivena.whitelist()
    def get_distinct_column_values(
        self, query: str, column_name: str, search_term: str | None = None, adhoc_filters: dict | None = None
    ):
        is_guest = trivena.session.user == "Guest"
        if is_guest and not self.is_public:
            raise trivena.PermissionError

        if not self.is_filter_column(query, column_name):
            trivena.throw(
                trivena._("This column is not available as a filter on this dashboard"),
                trivena.PermissionError,
            )

        doc = trivena.get_cached_doc("Insights Query v3", query)
        return doc.get_distinct_column_values(
            column_name, search_term=search_term, adhoc_filters=adhoc_filters
        )

    def is_filter_column(self, query, column_name):
        # a filter links a column as "links": { '<chart>': "`<query>`.`<column>`" }
        pattern = "^`([^`]+)`\\.`([^`]+)`$"
        items = trivena.parse_json(self.items)
        for item in items:
            if item["type"] != "filter":
                continue
            for linked_column in item.get("links", {}).values():
                match = re.match(pattern, linked_column)
                if match and match.groups() == (query, column_name):
                    return True
        return False

    def enqueue_update_dashboard_preview(self):
        if self.is_new() or not self.get_doc_before_save() or trivena.flags.in_patch:
            return

        prev_doc = self.get_doc_before_save()
        trivena.enqueue_doc(
            doctype=self.doctype,
            name=self.name,
            method="update_dashboard_preview",
            new_doc=self.as_dict(),
            prev_doc=prev_doc.as_dict(),
            enqueue_after_commit=True,
        )

    def update_dashboard_preview(self, new_doc, prev_doc):
        new_doc = trivena.parse_json(new_doc)
        prev_doc = trivena.parse_json(prev_doc)

        if new_doc["items"] == prev_doc["items"]:
            return

        self.generate_dashboard_preview()

    def generate_dashboard_preview(self):
        with generate_preview_key() as key:
            preview = get_page_preview(
                trivena.utils.get_url(get_app_url(f"/shared/dashboard/{self.name}")),
                headers={
                    "X-Insights-Preview-Key": key,
                },
            )
            file_url = create_preview_file(preview, self.name)
            random_hash = trivena.generate_hash()[0:4]
            file_url = f"{file_url}?{random_hash}"
            self.db_set("preview_image", file_url)
            return file_url

    def get_acess_data(self):
        DocShare = trivena.qb.DocType("DocShare")
        User = trivena.qb.DocType("User")

        shared_with = (
            trivena.qb.from_(DocShare)
            .left_join(User)
            .on(DocShare.user == User.name)
            .select(
                DocShare.user,
                DocShare.everyone,
                User.full_name,
                User.user_image,
                User.email,
            )
            .where(DocShare.share_doctype == "Insights Dashboard v3")
            .where(DocShare.share_name == self.name)
            .where((DocShare.read == 1) | (DocShare.write == 1))
            .run(as_dict=True)
        )

        org_access = False
        people_with_access = []
        for share in shared_with:
            if not share.everyone:
                people_with_access.append(
                    {
                        "full_name": share.full_name,
                        "user_image": share.user_image,
                        "email": share.email,
                    }
                )
            else:
                org_access = True

        return people_with_access, org_access

    @trivena.whitelist()
    def update_access(self, data: dict | str):
        if not trivena.has_permission("Insights Dashboard v3", ptype="share", doc=self.name):
            trivena.throw("You do not have permission to share this dashboard")

        data = trivena.parse_json(data)
        is_public = data.get("is_public")
        is_shared_with_organization = data.get("is_shared_with_organization")
        people_with_access = data.get("people_with_access") or []

        existing_shares = trivena.get_all(
            "DocShare",
            filters={
                "share_doctype": "Insights Dashboard v3",
                "share_name": self.name,
                "read": 1,
            },
            fields=["name", "user", "everyone"],
        )

        # remove all existing shares that are not in the new list
        for share in existing_shares:
            if share.user and share.user not in people_with_access:
                trivena.delete_doc("DocShare", share.name, ignore_permissions=True)

        # add new shares
        existing_share_users = [share.user for share in existing_shares if share.user]
        for user in people_with_access:
            if user not in existing_share_users:
                doc = DocShare.get_or_create_doc(
                    share_doctype="Insights Dashboard v3",
                    share_name=self.name,
                    user=user,
                )
                doc.read = 1
                doc.notify_by_email = 0
                doc.save(ignore_permissions=True)

        org_shares = [share for share in existing_shares if share.everyone]
        if is_shared_with_organization and not org_shares:
            doc = DocShare.get_or_create_doc(
                share_doctype="Insights Dashboard v3",
                share_name=self.name,
                everyone=1,
            )
            doc.read = 1
            doc.notify_by_email = 0
            doc.save(ignore_permissions=True)
        elif org_shares and not is_shared_with_organization:
            for share in org_shares:
                trivena.delete_doc("DocShare", share.name, ignore_permissions=True)

        self.db_set("is_public", is_public)

        if people_with_access:
            capture("dashboard_shared_with_user", "trivena_insights")
        if is_public:
            capture("dashboard_set_public", "trivena_insights")


def get_page_preview(url: str, headers: dict | None = None) -> bytes:
    # Newer Frappe renders previews in-process via headless Chromium — no
    # external service, and the site's own /assets and /files resolve locally.
    # Older versions fall back to the preview_generator HTTP service.
    try:
        from trivena_framework.utils.preview import get_preview_from_url
    except ImportError:
        return get_page_preview_via_service(url, headers)

    return get_preview_from_url(url, wait_for=1000, headers=headers or {}, format="jpeg")


def get_page_preview_via_service(url: str, headers: dict | None = None) -> bytes:
    PREVIEW_GENERATOR_URL = (
        trivena.conf.preview_generator_url
        or "https://preview.frappe.cloud/api/method/preview_generator.api.generate_preview_from_url"
    )

    response = requests.post(
        PREVIEW_GENERATOR_URL,
        json={
            "url": url,
            "headers": headers or {},
            "wait_for": 1000,
        },
    )
    if response.status_code == 200:
        return response.content
    else:
        exception = response.json()
        trivena.log_error(message=exception, title="Failed to generate preview")
        trivena.throw("Failed to generate preview")


def create_preview_file(content: bytes, dashboard_name: str):
    file_name = f"{dashboard_name}-preview.jpeg"
    file = File.get_or_create_doc(
        attached_to_doctype="Insights Dashboard v3",
        attached_to_name=dashboard_name,
        file_name=file_name,
        is_private=1,
    )
    if file.name:
        file.content = content
        file.save_file(overwrite=True)
        file.save()
    else:
        # insert file while ensuring file name is same as the one we want
        # first insert without content to reserve the file name (ignoring validate_file_on_disk)
        # then overwrite the file with the content
        file.flags.ignore_validate = True
        file.insert()
        file.flags.ignore_validate = False
        file.content = content
        file.save_file(overwrite=True)
        file.save()

    return file.file_url


@contextmanager
def generate_preview_key():
    try:
        key = trivena.generate_hash()
        trivena.cache.set_value(f"insights_preview_key:{key}", True)
        yield key
    finally:
        trivena.cache.delete_value(f"insights_preview_key:{key}")
