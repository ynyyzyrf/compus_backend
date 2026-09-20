"""Member list/detail filtering through the permission scope."""

from app.services import directory_service


def _names(page) -> set[str]:
    return {m.name for m in page.items}


def test_class_scope_member_list(ctx):
    page = directory_service.list_members(ctx.db, ctx.user("周可欣"), None, 1, 50)
    assert page.total == 1
    assert _names(page) == {"周可欣"}


def test_college_scope_includes_cross_department_classmates(ctx):
    page = directory_service.list_members(ctx.db, ctx.user("張晨"), None, 1, 50)
    # MAG, 張晨, 黃俊傑 (計算機) + 陳思遠 (軟件工程) — all inside the open college.
    assert _names(page) == {"MAG", "張晨", "黃俊傑", "陳思遠"}
    # Other colleges excluded.
    assert "林嘉怡" not in _names(page)


def test_department_scope_member_list(ctx):
    page = directory_service.list_members(ctx.db, ctx.user("林嘉怡"), None, 1, 50)
    assert _names(page) == {"林嘉怡"}


def test_search_by_name_and_org_path(ctx):
    by_name = directory_service.list_members(ctx.db, ctx.user("張晨"), "陳", 1, 50)
    assert _names(by_name) == {"陳思遠"}

    by_org = directory_service.list_members(ctx.db, ctx.user("張晨"), "軟件", 1, 50)
    assert _names(by_org) == {"陳思遠"}

    # A class-scoped user cannot search outside their scope.
    blocked = directory_service.list_members(ctx.db, ctx.user("周可欣"), "張", 1, 50)
    assert blocked.total == 0


def test_member_detail_respects_scope(ctx):
    db = ctx.db
    # College-open viewer can read a member in another department.
    seen = directory_service.get_member(db, ctx.user("張晨"), ctx.user("陳思遠").id)
    assert seen is not None
    assert seen.phone == "13800000004"

    # Cross-college access is denied (returns None -> API maps to 404).
    denied = directory_service.get_member(db, ctx.user("周可欣"), ctx.user("張晨").id)
    assert denied is None
