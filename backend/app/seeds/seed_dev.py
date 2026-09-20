"""Idempotent dev seed data.

Usage:
    uv run python -m app.seeds.seed_dev          # reset + reseed dev data
    uv run python -m app.seeds.seed_dev --no-reset  # only seed when empty

Builds the prototype org tree, demo members with primary memberships, and
directory_permissions showcasing all three readability scopes:

* 信息工程分院 -> college-wide readable
* 工商管理系   -> department-wide readable
* all classes  -> default same-class readable
"""

import sys

from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.models.activity import (
    Activity,
    ActivityCheckin,
    ActivitySignup,
    Photo,
)
from app.models.content import Article, ArticleScope
from app.models.enums import (
    DirectoryScope,
    OrgType,
    Role,
    Status,
)
from app.models.organization import (
    DirectoryPermission,
    Membership,
    Organization,
)
from app.models.relay import Relay, RelayField, RelayResponse
from app.models.user import User

# (college, department, class)
ORG_TREE: dict[str, dict[str, list[str]]] = {
    "信息工程分院": {
        "計算機系": ["2016級1班", "2017級2班"],
        "軟件工程系": ["2018級3班"],
        "數據科學系": ["2019級2班"],
    },
    "商學分院": {
        "工商管理系": ["2017級2班", "2018級4班"],
        "市場營銷系": ["2019級1班"],
    },
    "藝術設計分院": {
        "視覺設計系": ["2015級1班"],
        "工業設計系": ["2016級3班"],
    },
}

# name -> (openid, role, college, department, class, phone)
MEMBERS: list[tuple[str, str, str, str, str, str, str | None]] = [
    ("MAG", "dev-admin", Role.SUPER_ADMIN, "信息工程分院", "計算機系", "2016級1班", "13800000001"),
    ("張晨", "dev-zhangchen", Role.USER, "信息工程分院", "計算機系", "2016級1班", "13800000002"),
    ("黃俊傑", "dev-huang", Role.USER, "信息工程分院", "計算機系", "2016級1班", "13800000003"),
    ("陳思遠", "dev-chen", Role.USER, "信息工程分院", "軟件工程系", "2018級3班", "13800000004"),
    ("林嘉怡", "dev-lin", Role.USER, "商學分院", "工商管理系", "2017級2班", "13800000005"),
    ("周可欣", "dev-zhou", Role.USER, "商學分院", "市場營銷系", "2019級1班", "13800000006"),
    ("王子謙", "dev-wang", Role.USER, "藝術設計分院", "視覺設計系", "2015級1班", "13800000007"),
]

COLLEGE_OPEN = "信息工程分院"
DEPARTMENT_OPEN = ("商學分院", "工商管理系")


def reset(db) -> None:
    for model in (
        RelayResponse,
        RelayField,
        Relay,
        ArticleScope,
        Article,
        Photo,
        ActivityCheckin,
        ActivitySignup,
        Activity,
        Membership,
        DirectoryPermission,
        User,
        Organization,
    ):
        db.execute(delete(model))
    db.flush()


def build_orgs(db) -> tuple[Organization, dict[tuple, Organization]]:
    school = Organization(name="XX校友組織", type=OrgType.SCHOOL, parent_id=None, sort_order=0)
    db.add(school)
    db.flush()

    index: dict[tuple, Organization] = {}
    college_sort = dept_sort = class_sort = 0
    for college_name, depts in ORG_TREE.items():
        college_sort += 1
        college = Organization(
            name=college_name,
            type=OrgType.COLLEGE,
            parent_id=school.id,
            sort_order=college_sort,
        )
        db.add(college)
        db.flush()
        index[("college", college_name)] = college

        for dept_name, classes in depts.items():
            dept_sort += 1
            dept = Organization(
                name=dept_name,
                type=OrgType.DEPARTMENT,
                parent_id=college.id,
                sort_order=dept_sort,
            )
            db.add(dept)
            db.flush()
            index[("department", college_name, dept_name)] = dept

            for class_name in classes:
                class_sort += 1
                klass = Organization(
                    name=class_name,
                    type=OrgType.CLASS,
                    parent_id=dept.id,
                    sort_order=class_sort,
                )
                db.add(klass)
                db.flush()
                index[("class", college_name, dept_name, class_name)] = klass
    return school, index


def build_permissions(db, index: dict[tuple, Organization]) -> None:
    # Default: every class is same-class readable.
    for key, node in index.items():
        if key[0] == "class":
            db.add(
                DirectoryPermission(
                    organization_id=node.id,
                    scope_type=DirectoryScope.CLASS,
                    is_enabled=True,
                )
            )
    # College-wide open.
    college = index[("college", COLLEGE_OPEN)]
    db.add(
        DirectoryPermission(
            organization_id=college.id,
            scope_type=DirectoryScope.COLLEGE,
            is_enabled=True,
        )
    )
    # Department-wide open.
    dept = index[("department", *DEPARTMENT_OPEN)]
    db.add(
        DirectoryPermission(
            organization_id=dept.id,
            scope_type=DirectoryScope.DEPARTMENT,
            is_enabled=True,
        )
    )


def build_users(db, index: dict[tuple, Organization]) -> None:
    for name, openid, role, college, dept, klass_name, phone in MEMBERS:
        user = User(
            openid=openid,
            name=name,
            role=role,
            status=Status.ACTIVE,
            phone=phone,
            wechat_id=f"wx_{openid}",
            email=f"{openid}@example.com",
            bio="",
        )
        db.add(user)
        db.flush()
        klass = index[("class", college, dept, klass_name)]
        db.add(
            Membership(
                user_id=user.id,
                organization_id=klass.id,
                is_primary=True,
            )
        )
    db.flush()


def run(reset_data: bool = True) -> None:
    db = SessionLocal()
    try:
        existing = db.scalars(select(Organization).limit(1)).first()
        if existing and not reset_data:
            print("數據已存在，跳過（使用 --reset 可重建）。")
            return
        if existing:
            reset(db)
        _, index = build_orgs(db)
        build_permissions(db, index)
        build_users(db, index)
        db.commit()
        print("[OK] seed data written.")
        print("   mock 登錄默認進入超管 MAG；可用 /auth/dev-impersonate 切換：")
        for uid in db.scalars(select(User.id).order_by(User.id)):
            print(f"   - user_id={uid}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run(reset_data="--no-reset" not in sys.argv)
