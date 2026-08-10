import io
from contextlib import suppress

import trivena_framework as trivena
import pandas as pd
from trivena_framework.utils.file_manager import save_file

from trivena_insights.api import import_csv_data
from trivena_insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import db_connections
from trivena_insights.insights.doctype.insights_table_v3.insights_table_v3 import get_table_name
from trivena_insights.tests.base import InsightsIntegrationTestCase
from trivena_insights.tests.factories import DT


class TestUploadedFileImports(InsightsIntegrationTestCase):
    def before_test(self):
        self.uploaded_files = []
        self.imported_tables = []

    def after_test(self):
        if self.imported_tables and trivena.db.exists(DT.DATA_SOURCE, "uploads"):
            data_source = trivena.get_doc(DT.DATA_SOURCE, "uploads")
            with suppress(Exception):
                with data_source.write_connection() as db:
                    for table_name in self.imported_tables:
                        with suppress(Exception):
                            db.drop_table(table_name, force=True)

        for table_name in self.imported_tables:
            table_docname = get_table_name("uploads", table_name)
            with suppress(Exception):
                trivena.delete_doc(DT.TABLE, table_docname, force=True)

        for file_name in self.uploaded_files:
            with suppress(Exception):
                trivena.delete_doc("File", file_name, force=True)

    def _unique_name(self, prefix: str, suffix: str | None = None) -> str:
        name = f"{prefix}_{trivena.generate_hash(length=8)}"
        return f"{name}.{suffix}" if suffix else name

    def _save_private_csv(self, rows: list[dict]) -> str:
        content = pd.DataFrame(rows).to_csv(index=False).encode()
        file_doc = save_file(self._unique_name("insights_upload", "csv"), content, None, None, is_private=1)
        self.uploaded_files.append(file_doc.name)
        return file_doc.name

    def _save_private_xlsx(self, rows: list[dict]) -> str:
        output = io.BytesIO()
        pd.DataFrame(rows).to_excel(output, index=False, engine="openpyxl")
        file_doc = save_file(
            self._unique_name("insights_upload", "xlsx"), output.getvalue(), None, None, is_private=1
        )
        self.uploaded_files.append(file_doc.name)
        return file_doc.name

    def _assert_imported_rows(self, table_name: str, expected_rows: list[dict]):
        self.assertTrue(trivena.db.exists(DT.DATA_SOURCE, "uploads"))
        self.assertTrue(trivena.db.exists(DT.TABLE, get_table_name("uploads", table_name)))

        data_source = trivena.get_doc(DT.DATA_SOURCE, "uploads")
        with db_connections():
            rows = data_source.get_ibis_table(table_name).order_by("id").execute().to_dict("records")

        self.assertEqual(rows, expected_rows)

    def test_import_csv_data_imports_private_csv_upload(self):
        rows = [
            {"id": 1, "name": "Alpha"},
            {"id": 2, "name": "Beta"},
        ]
        file_name = self._save_private_csv(rows)
        table_name = self._unique_name("upload_csv")
        self.imported_tables.append(table_name)

        import_csv_data(file_name, table_name)

        self._assert_imported_rows(table_name, rows)

    def test_import_csv_data_imports_private_excel_upload(self):
        rows = [
            {"id": 1, "name": "Gamma"},
            {"id": 2, "name": "Delta"},
        ]
        file_name = self._save_private_xlsx(rows)
        table_name = self._unique_name("upload_xlsx")
        self.imported_tables.append(table_name)

        import_csv_data(file_name, table_name)

        self._assert_imported_rows(table_name, rows)
