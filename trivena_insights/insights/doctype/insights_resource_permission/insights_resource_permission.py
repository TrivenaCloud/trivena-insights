# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from trivena_framework.model.document import Document


class InsightsResourcePermission(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from trivena_framework.types import DF

        name: DF.Int | None
        parent: DF.Data
        parentfield: DF.Data
        parenttype: DF.Data
        resource_name: DF.DynamicLink
        resource_type: DF.Link
        table_restrictions: DF.Data | None
    # end: auto-generated types

    pass
