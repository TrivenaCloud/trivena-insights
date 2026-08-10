# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from trivena_framework.model.document import Document


class InsightsQueryReference(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from trivena_framework.types import DF

        data_source: DF.Data | None
        query: DF.Link
        ref_query: DF.Link | None
        ref_type: DF.Literal["Table", "Query"]
        table_name: DF.Data | None
    # end: auto-generated types

    pass
