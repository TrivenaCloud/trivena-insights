# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import trivena_framework as trivena
from trivena_framework.model.document import Document


class InsightsTableImportLog(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from trivena_framework.types import DF

        batch_size: DF.Int
        data_source: DF.Data
        ended_at: DF.Datetime | None
        error: DF.Code | None
        import_job: DF.Link | None
        memory_limit: DF.Int
        output: DF.Code | None
        parquet_file: DF.Text | None
        query: DF.Code | None
        row_limit: DF.Int
        row_size: DF.Float
        rows_imported: DF.Int
        started_at: DF.Datetime | None
        status: DF.Literal["In Progress", "Completed", "Failed"]
        table_name: DF.Data
        time_taken: DF.Int
    # end: auto-generated types

    def log_output(self, message: str, commit: bool = False):
        if not self.output:
            self.output = ""
        self.output += message + "\n"
        self.db_update()
        commit and trivena.db.commit()

    @trivena.whitelist()
    def mark_as_failed(self):
        trivena.only_for("System Manager")
        self.status = "Failed"
        self.db_update()
