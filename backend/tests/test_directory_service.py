"""Member list/detail filtering through the permission scope."""

from app.services import directory_service


def _names(page) -> set[str]:
    return {m.name for m in page.items}


def test_class_scope_member_list(ctx):
    page = directory_service.list_members(ctx.db, ctx.user("周可欣"), None, 1, 50)
    assert page.total == 1
    assert _names(page) == {"周可欣"}


def test_college_scope_respects_default_basic_visibility(ctx):
    page = directory_service.list_members(ctx.db, ctx.user("張晨"), None, 1, 50)
    assert _names(page) == {"MAG", "張晨", "黃俊傑"}


def test_department_scope_member_list(ctx):
    page = directory_service.list_members(ctx.db, ctx.user("林嘉怡"), None, 1, 50)
    assert _names(page) == {"林嘉怡"}


def test_search_by_name_and_org_path(ctx):
    ctx.user("陳思遠").alumni_discoverable = True
    ctx.db.flush()
    by_name = directory_service.list_members(ctx.db, ctx.user("張晨"), "陳", 1, 50, discover=True)
    assert _names(by_name) == {"陳思遠"}

    by_org = directory_service.list_members(ctx.db, ctx.user("張晨"), "軟件", 1, 50, discover=True)
    assert _names(by_org) == {"陳思遠"}

    # A class-scoped user cannot search outside their scope.
    blocked = directory_service.list_members(ctx.db, ctx.user("周可欣"), "張", 1, 50)
    assert blocked.total == 0


def test_member_detail_respects_scope(ctx):
    db = ctx.db
    seen = directory_service.get_member(db, ctx.user("張晨"), ctx.user("黃俊傑").id)
    assert seen is not None
    assert seen.phone is None
    assert directory_service.get_member(db, ctx.user("張晨"), ctx.user("陳思遠").id) is None

    # Cross-college access is denied (returns None -> API maps to 404).
    denied = directory_service.get_member(db, ctx.user("周可欣"), ctx.user("張晨").id)
    assert denied is None
