import trivena_framework as trivena
from trivena_framework.translate import get_all_translations


@trivena.whitelist(allow_guest=True, methods=["GET"])
def get_translations():
    language = None
    if trivena.session.user != "Guest":
        language = trivena.db.get_value("User", trivena.session.user, "language")
    if not language:
        language = trivena.db.get_single_value("System Settings", "language")
    return get_all_translations(language)
