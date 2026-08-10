import trivena_framework as trivena

from trivena_insights.decorators import insights_whitelist, validate_type


@insights_whitelist()
@validate_type
def get_alerts(query: str):
    return trivena.get_list(
        "Insights Alert",
        filters={"query": query},
        fields=["*"],
    )
