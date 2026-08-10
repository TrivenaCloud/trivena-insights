# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from trivena_framework.model.document import Document


class InsightsFolder(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from trivena_framework.types import DF

		is_expanded: DF.Check
		sort_order: DF.Int
		title: DF.Data
		type: DF.Literal["query", "chart"]
		workbook: DF.Link
	# end: auto-generated types
	pass
