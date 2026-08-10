import trivena_framework as trivena


def execute():
    if trivena.db.exists("Insights Table v3", {"stored": 1}):
        trivena.db.set_single_value("Insights Settings", "enable_data_store", 1)
