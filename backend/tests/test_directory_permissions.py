"""Core permission rules (PRD §8, acceptance 30.2)."""

from app.services.directory_permission import readable_scope
from app.services.org_tree import load_org_tree


def _class_names(db, class_ids: set[int]) -> set[str]:
    from app.models.organization import Organization
    from sqlalchemy import select

    rows = db.scalars(
        select(Organization).where(Organization.id.in_(class_ids))
    ).all()
    return {r.name for r in rows}


def test_college_scope_opens_whole_college(ctx):
    db = ctx.db
    tree = load_org_tree(db)
    scope = readable_scope(db, tree, ctx.user("張晨"))

    assert scope.scope_level == "college"
    names = _class_names(db, scope.class_ids)
    # All four classes under 信息工程分院 are visible...
    assert {"2016級1班", "2017級2班", "2018級3班", "2019級2班"} <= names
    # ...but nothing from other colleges (class names may repeat, so count too).
    assert len(scope.class_ids) == 4


def test_department_scope_opens_only_that_department(ctx):
    db = ctx.db
    tree = load_org_tree(db)
    scope = readable_scope(db, tree, ctx.user("林嘉怡"))

    assert scope.scope_level == "department"
    assert len(scope.class_ids) == 2  # 工商管理系 has two classes
    # 市場營銷系 stays hidden.
    market_class = ctx.class_id_for("周可欣")
    assert market_class not in scope.class_ids


def test_default_is_same_class_only(ctx):
    db = ctx.db
    tree = load_org_tree(db)
    scope = readable_scope(db, tree, ctx.user("周可欣"))

    assert scope.scope_level == "class"
    assert scope.class_ids == {ctx.class_id_for("周可欣")}
    # Ancestor containers still present for tree navigation.
    college = ctx.org_by_name("商學分院", ctx.org_by_name("XX校友組織", None).id)
    assert college.id in scope.visible_node_ids


def test_super_admin_sees_everything(ctx):
    db = ctx.db
    tree = load_org_tree(db)
    scope = readable_scope(db, tree, ctx.user("MAG"))

    assert scope.scope_level == "all"
    assert len(scope.class_ids) == 9  # 4 + 3 + 2 seeded classes
    assert scope.visible_node_ids == set(tree.nodes.keys())
