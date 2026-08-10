# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import trivena_framework as trivena
import ibis


def get_mssql_connection(data_source):
    if not trivena.conf.get("mssql_odbc_driver"):
        trivena.throw(
            "MSSQL ODBC driver path not configured. Please set it in common_site_config.json"
            " under 'mssql_odbc_driver' key."
            " Eg. 'mssql_odbc_driver': '/usr/local/lib/libtdsodbc.so' or 'FreeTDS'"
        )

    password = data_source.get_password(raise_exception=False)
    data_source.port = int(data_source.port or 1433)

    return ibis.mssql.connect(
        host=data_source.host,
        port=data_source.port,
        user=data_source.username,
        password=password,
        database=data_source.database_name,
        driver=trivena.conf.get("mssql_odbc_driver"),
    )
