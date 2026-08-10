import trivena_framework as trivena
from trivena_framework import _

from trivena_insights.decorators import insights_whitelist
from trivena_insights.utils import DocShare


@insights_whitelist()
def get_workbooks(
    search_term: str | None = None,
    limit: int = 100,
    scope: str | None = None,
):
    """Return workbooks accessible to the current user.

    scope:
        "owned"  -> only workbooks owned by the current user
        "shared" -> only workbooks owned by someone else (still permission filtered)
        None     -> all accessible workbooks
    """
    filters = {}
    if scope == "owned":
        filters["owner"] = trivena.session.user
    elif scope == "shared":
        filters["owner"] = ["!=", trivena.session.user]

    or_filters = {"title": ["like", f"%{search_term}%"]} if search_term else None

    workbooks = trivena.get_list(
        "Insights Workbook",
        filters=filters,
        or_filters=or_filters,
        fields=[
            "name",
            "title",
            "owner",
            "creation",
            "modified",
        ],
        limit=limit,
    )
    # FIX: figure out how to use trivena.qb while respecting permissions
    # TODO: use trivena.qb to get the view count
    workbook_names = [workbook["name"] for workbook in workbooks]
    workbook_views = trivena.get_all(
        "View Log",
        filters={
            "reference_doctype": "Insights Workbook",
            "reference_name": ["in", workbook_names],
        },
        fields=["reference_name", "name"],
    )
    for workbook in workbooks:
        views = [view for view in workbook_views if str(view["reference_name"]) == str(workbook["name"])]
        workbook["views"] = len(views)

    # batch the share lookups into two grouped queries instead of ~2 per
    # workbook (avoids an N+1 over the whole list)
    org_shared, shared_users = _workbook_shares(workbook_names)
    for workbook in workbooks:
        # share_name is stored as a string; workbook name may be an int — cast to match
        name = str(workbook["name"])
        if name in org_shared:
            workbook["shared_with_organization"] = True
            continue
        workbook["shared_with"] = [user for user in shared_users.get(name, []) if user != workbook["owner"]]

    return workbooks


def _workbook_shares(names: list[str]) -> tuple[set, dict]:
    """Return (org-shared workbook names, {workbook name -> [users it's read-shared with]}).

    Two queries for the whole list instead of an exists-check + fetch per workbook.
    Keys are stringified since DocShare.share_name is stored as a string.
    """
    if not names:
        return set(), {}

    org_shared = {
        str(name)
        for name in trivena.get_all(
            "DocShare",
            filters={
                "share_doctype": "Insights Workbook",
                "share_name": ["in", names],
                "everyone": 1,
                "read": 1,
            },
            pluck="share_name",
        )
    }

    shared_users: dict[str, list] = {}
    rows = trivena.get_all(
        "DocShare",
        filters={
            "share_doctype": "Insights Workbook",
            "share_name": ["in", names],
            "read": 1,
        },
        fields=["share_name", "user"],
    )
    for row in rows:
        shared_users.setdefault(str(row["share_name"]), []).append(row["user"])

    return org_shared, shared_users


@insights_whitelist()
def import_workbook(workbook: dict):
    from trivena_insights.insights.doctype.insights_workbook.insights_workbook import import_workbook

    return import_workbook(workbook)


@insights_whitelist()
def get_share_permissions(workbook_name: str):
    if not trivena.has_permission("Insights Workbook", ptype="share", doc=workbook_name):
        trivena.throw(_("You do not have permission to share this workbook"), trivena.PermissionError)

    DocShare = trivena.qb.DocType("DocShare")
    User = trivena.qb.DocType("User")

    user_permissions = (
        trivena.qb.from_(DocShare)
        .left_join(User)
        .on(DocShare.user == User.name)
        .select(
            DocShare.user,
            DocShare.read,
            DocShare.write,
            DocShare.share,
            User.full_name,
        )
        .where(DocShare.share_doctype == "Insights Workbook")
        .where(DocShare.share_name == workbook_name)
        .where(DocShare.everyone == 0)
        .run(as_dict=True)
    )
    owner = trivena.db.get_value("Insights Workbook", workbook_name, "owner")
    user_permissions.append(
        {
            "user": owner,
            "full_name": trivena.get_value("User", owner, "full_name"),
            "read": 1,
            "write": 1,
        }
    )

    public_docshare = trivena.db.get_value(
        "DocShare",
        filters={
            "share_doctype": "Insights Workbook",
            "share_name": workbook_name,
            "everyone": 1,
        },
        fieldname=["read", "write"],
        as_dict=True,
    )
    organization_access = None
    if public_docshare:
        organization_access = "edit" if public_docshare["write"] else "view"

    return {
        "user_permissions": user_permissions,
        "organization_access": organization_access,
    }


@insights_whitelist()
def update_share_permissions(
    workbook_name: str, user_permissions: dict, organization_access: str | None = None
):
    if not trivena.has_permission("Insights Workbook", ptype="share", doc=workbook_name):
        trivena.throw(_("You do not have permission to share this workbook"), trivena.PermissionError)

    existing_shares = trivena.get_all(
        "DocShare",
        filters={
            "share_doctype": "Insights Workbook",
            "share_name": workbook_name,
        },
        fields=["name", "user", "everyone"],
    )

    allowed_users = {permission["user"] for permission in user_permissions}
    for share in existing_shares:
        if share.user and share.user not in allowed_users:
            trivena.delete_doc("DocShare", share.name, ignore_permissions=True)

    for permission in user_permissions:
        doc = DocShare.get_or_create_doc(
            share_doctype="Insights Workbook",
            share_name=workbook_name,
            user=permission["user"],
        )
        doc.read = permission["read"]
        doc.write = permission["write"]
        doc.notify_by_email = 0
        doc.save(ignore_permissions=True)

    public_docshare = DocShare.get_or_create_doc(
        share_doctype="Insights Workbook",
        share_name=workbook_name,
        everyone=1,
    )
    if organization_access:
        public_docshare.read = 1
        public_docshare.write = organization_access == "edit"
        public_docshare.notify_by_email = 0
        public_docshare.save(ignore_permissions=True)
    elif public_docshare.name:
        public_docshare.delete(ignore_permissions=True)


# folder Management APIs


@insights_whitelist()
def create_folder(workbook: str, title: str, folder_type: str):
    """Create a new folder in workbook"""
    if not trivena.has_permission("Insights Workbook", ptype="write", doc=workbook):
        trivena.throw(_("You do not have permission to modify this workbook"), trivena.PermissionError)

    current_folders = trivena.db.count("Insights Folder", filters={"workbook": workbook, "type": folder_type})

    folder = trivena.new_doc("Insights Folder")
    folder.workbook = workbook
    folder.title = title
    folder.type = folder_type
    folder.sort_order = current_folders
    folder.insert()

    return folder.name


@insights_whitelist()
def rename_folder(folder_name: str, new_title: str):
    """Rename a folder"""
    folder = trivena.get_doc("Insights Folder", folder_name)
    if not trivena.has_permission("Insights Workbook", ptype="write", doc=folder.workbook):
        trivena.throw(_("You do not have permission to modify this workbook"), trivena.PermissionError)

    folder.title = new_title
    folder.save()

    return folder.name


@insights_whitelist()
def delete_folder(folder_name: str, move_items_to_root: bool = True):
    """Delete folder and move items to root"""
    folder = trivena.get_doc("Insights Folder", folder_name)
    if not trivena.has_permission("Insights Workbook", ptype="write", doc=folder.workbook):
        trivena.throw(_("You do not have permission to modify this workbook"), trivena.PermissionError)

    if move_items_to_root:
        # move all queries to root
        trivena.db.set_value(
            "Insights Query v3",
            {"folder": folder_name},
            "folder",
            None,
            update_modified=False,
        )
        # move all charts to root
        trivena.db.set_value(
            "Insights Chart v3",
            {"folder": folder_name},
            "folder",
            None,
            update_modified=False,
        )

    trivena.delete_doc("Insights Folder", folder_name)


@insights_whitelist()
def toggle_folder_expanded(folder_name: str, is_expanded: bool):
    """Toggle folder expanded state"""
    folder = trivena.get_doc("Insights Folder", folder_name)
    if not trivena.has_permission("Insights Workbook", ptype="read", doc=folder.workbook):
        trivena.throw(_("You do not have permission to modify this workbook"), trivena.PermissionError)

    folder.db_set("is_expanded", is_expanded, update_modified=False)


@insights_whitelist()
def move_item_to_folder(item_type: str, item_name: str, folder_name: str | None = None):
    """Move a query/chart to a folder"""
    doctype = "Insights Query v3" if item_type == "query" else "Insights Chart v3"
    item = trivena.get_doc(doctype, item_name)

    if not trivena.has_permission("Insights Workbook", ptype="write", doc=item.workbook):
        trivena.throw(_("You do not have permission to modify this workbook"), trivena.PermissionError)

    if folder_name:
        folder = trivena.get_doc("Insights Folder", folder_name)
        if folder.workbook != item.workbook:
            trivena.throw(_("Folder and item must belong to the same workbook"))

    item.db_set("folder", folder_name, update_modified=False)


@insights_whitelist()
def update_sort_orders(workbook: str, items: list):
    """Bulk update sort orders"""
    if not trivena.has_permission("Insights Workbook", ptype="write", doc=workbook):
        trivena.throw(_("You do not have permission to modify this workbook"), trivena.PermissionError)

    for item in items:
        if item["type"] == "folder":
            trivena.db.set_value(
                "Insights Folder",
                item["name"],
                {
                    "sort_order": item["sort_order"],
                },
                update_modified=False,
            )
        elif item["type"] == "query":
            trivena.db.set_value(
                "Insights Query v3",
                item["name"],
                {
                    "sort_order": item["sort_order"],
                    "folder": item.get("folder"),
                },
                update_modified=False,
            )
        elif item["type"] == "chart":
            trivena.db.set_value(
                "Insights Chart v3",
                item["name"],
                {
                    "sort_order": item["sort_order"],
                    "folder": item.get("folder"),
                },
                update_modified=False,
            )

    trivena.db.commit()
