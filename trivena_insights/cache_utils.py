# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import hashlib

import trivena_framework as trivena

EXPIRY = 60 * 10


def make_digest(*args):
    key = ""
    for arg in args:
        if isinstance(arg, dict):
            key += trivena.as_json(arg)
        key += trivena.cstr(arg)
    return hashlib.md5(key.encode("utf-8")).hexdigest()


def get_or_set_cache(key, func, force=False, expiry=EXPIRY):
    key = f"insights|{key}"
    cached_value = trivena.cache().get_value(key)
    if cached_value is not None and not force:
        return cached_value

    value = func()
    trivena.cache().set_value(key, value, expires_in_sec=expiry)
    return value


@trivena.whitelist()
def reset_insights_cache():
    trivena.only_for("System Manager")
    trivena.cache().delete_keys("insights*")
