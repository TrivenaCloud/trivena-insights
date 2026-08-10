# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import trivena_framework as trivena
from trivena_framework.model.document import Document
from trivena_framework.utils import add_days, get_datetime, now, validate_email_address

EXPIRY_DAYS = 1


class InsightsUserInvitation(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from trivena_framework.types import DF

        accepted_at: DF.Datetime | None
        email: DF.Data
        email_sent_at: DF.Datetime | None
        invited_by: DF.Link | None
        key: DF.Data | None
        name: DF.Int | None
        status: DF.Literal["Pending", "Accepted", "Expired"]
    # end: auto-generated types

    def has_expired(self):
        return self.status == "Pending" and get_datetime(self.creation) < get_datetime(
            add_days(now(), -EXPIRY_DAYS)
        )

    def before_insert(self):
        validate_email_address(self.email, True)
        self.key = trivena.generate_hash(length=12)
        self.invited_by = trivena.session.user
        self.status = "Pending"

    def after_insert(self):
        self.invite_via_email()

    def invite_via_email(self):
        invite_link = trivena.utils.get_url(
            f"/api/method/insights.api.user.accept_invitation?key={self.key}"
        )
        if trivena.local.dev_server:
            print(f"Invite link for {self.email}: {invite_link}")

        title = "Insights"
        template = "insights_invitation"

        trivena.sendmail(
            recipients=self.email,
            subject=f"{title} Invitation",
            template=template,
            args={"title": title, "invite_link": invite_link},
            now=True,
        )
        self.db_set("email_sent_at", trivena.utils.now())

    @trivena.whitelist()
    def accept_invitation(self):
        trivena.only_for("System Manager")
        self.accept()

    def accept(self):
        if self.has_expired():
            self.db_set("status", "Expired", commit=True)
            trivena.throw("Invalid or expired key")

        if self.status == "Expired":
            trivena.throw("Invalid or expired key")

        if self.status == "Accepted":
            trivena.throw("Invitation already accepted")

        user = self.create_user_if_not_exists()
        user.append_roles("Insights User")
        user.save(ignore_permissions=True)

        self.status = "Accepted"
        self.accepted_at = trivena.utils.now()
        self.save(ignore_permissions=True)

    def create_user_if_not_exists(self):
        if not trivena.db.exists("User", self.email):
            first_name = self.email.split("@")[0].title()
            user = trivena.get_doc(
                doctype="User",
                user_type="Website User",
                email=self.email,
                send_welcome_email=0,
                first_name=first_name,
            ).insert(ignore_permissions=True)
        else:
            user = trivena.get_doc("User", self.email)
        return user
