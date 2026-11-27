"""One-off, backed-up cleanup of the known legacy Zeabur example data.

Connection: CAMPUS_MAINTENANCE_DATABASE_URL (never stored in reports).
Default: read-only preview. --apply requires --backup-dir outside the checkout.
Requires SQLAlchemy, psycopg and optional maintenance-only opencc-python-reimplemented.
This script is never run automatically on deployment.
"""
import argparse
import hashlib
import json
import os
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import MetaData, create_engine, insert, select, text, update


TEXT_FIELDS = {
    "organizations": {"name"},
    "users": {"name", "name_en", "profession", "profession_en", "city", "bio",
              "missing_class_note", "company_name", "company_address", "position",
              "business_description", "referrals_needed", "personal_experience",
              "resources_offered", "chamber_chapter"},
    "articles": {"title", "summary", "content"},
    "activities": {"title", "description", "location", "organizer"},
    "activity_signups": {"remark"},
    "relays": {"title", "description"},
    "relay_fields": {"label", "options_json"},
    "relay_responses": {"response_json"},
    "alumni_connections": {"message"},
    "alumni_messages": {"message"},
}
PROTECTED = re.compile(
    r'(<script\b[^>]*>.*?</script\s*>|<style\b[^>]*>.*?</style\s*>|<[^>]*>'
    r'|(?:https?://|data:|/(?:storage|assets|uploads|api)/)[^\s<>"\x27]+'
    r'|&(?:#\d+|#x[0-9a-f]+|\w+);)', re.I | re.S,
)
LEGACY = {
    1: ("school", None, {"校友商會", "校友商会"}),
    2: ("college", 1, {"科技與創新分會", "科技与创新分会"}),
    3: ("college", 1, {"企業服務分會", "企业服务分会"}),
    4: ("department", 2, {"AI 與軟件系", "AI 与软件系"}),
    5: ("department", 2, {"跨境電商系", "跨境电商系"}),
    6: ("department", 3, {"財稅法務系", "财税法务系"}),
    7: ("department", 3, {"品牌市場系", "品牌市场系"}),
    8: ("class", 4, {"AI 工具班"}),
    9: ("class", 4, {"SaaS 創業班", "SaaS 创业班"}),
    10: ("class", 5, {"品牌出海班"}),
    11: ("class", 6, {"企業財稅班", "企业财税班"}),
    12: ("class", 7, {"增長營銷班", "增长营销班"}),
}
SAMPLE_NAMES = {
    1: "圆螺岭示例学校", 2: "信息工程学院", 3: "经济管理学院",
    4: "计算机系", 5: "电子信息系", 6: "工商管理系", 7: "财务管理系",
    8: "2016级1班", 9: "2017级1班", 10: "2016级1班",
    11: "2016级1班", 12: "2017级1班",
}
MAJORS = [
    {"name": "软件工程", "parent_id": 4},
    {"name": "电子信息工程", "parent_id": 5},
    {"name": "工商管理", "parent_id": 6},
    {"name": "会计学", "parent_id": 7},
]
CLASS_MAJORS = {8: "软件工程", 9: "软件工程", 10: "电子信息工程", 11: "工商管理", 12: "会计学"}


def simplify_value(value, convert):
    if isinstance(value, str):
        return "".join(part if index % 2 else convert(part)
                       for index, part in enumerate(PROTECTED.split(value)))
    if isinstance(value, list):
        return [simplify_value(item, convert) for item in value]
    if isinstance(value, dict):
        # Keys may be stable form-field identifiers, not presentation labels.
        return {key: simplify_value(item, convert) for key, item in value.items()}
    return value


def write_durable_json(path, value):
    payload = json.dumps(value, ensure_ascii=False, default=str, indent=2).encode("utf-8")
    # Binary mode prevents Windows newline translation from altering the digest.
    with path.open("xb") as f:
        f.write(payload)
        f.flush()
        os.fsync(f.fileno())
    if path.read_bytes() != payload:
        raise OSError("Backup verification failed")


def sample_changes(rows):
    by_id = {row["id"]: row for row in rows}
    if len(rows) == 16 and all(by_id.get(i, {}).get("name") == name for i, name in SAMPLE_NAMES.items()):
        return {}, []  # Already applied; validation below still checks the paths.
    if set(by_id) != set(LEGACY):
        raise ValueError("Organization IDs differ from the reviewed legacy example; refusing to guess")
    for node_id, (kind, parent, names) in LEGACY.items():
        row = by_id[node_id]
        if (row["type"], row["parent_id"]) != (kind, parent) or row["name"] not in names:
            raise ValueError(f"Organization {node_id} differs from the reviewed legacy example")
    changes = {i: {"name": name} for i, name in SAMPLE_NAMES.items()}
    for class_id, major in CLASS_MAJORS.items():
        changes[class_id].update(major_key=major, entry_year=2017 if class_id in (9, 12) else 2016)
    return changes, MAJORS


def snapshot(conn, tables):
    return {name: sorted([dict(row) for row in conn.execute(select(table)).mappings()],
                         key=lambda row: json.dumps(row, default=str, sort_keys=True))
            for name, table in tables.items()}


def text_changes(data, convert):
    changes = []
    for name, fields in TEXT_FIELDS.items():
        for row in data.get(name, []):
            values = {}
            for field in fields & row.keys():
                value = simplify_value(row[field], convert)
                if name == "articles" and isinstance(value, str):
                    value = value.replace("校友商会小程序", "圆螺岭同学录小程序")
                if value != row[field]:
                    values[field] = value
            if values:
                changes.append((name, row, values))
    return changes


def validate(data, before=None):
    nodes = {r["id"]: r for r in data["organizations"]}
    classes = {i for i, row in nodes.items() if row["type"] == "class"}
    assert classes == set(CLASS_MAJORS), "Class IDs changed"
    for class_id in classes:
        chain, seen = [], set()
        current = class_id
        while current is not None:
            assert current in nodes and current not in seen, "Invalid parent or cycle"
            seen.add(current)
            chain.append(nodes[current])
            current = nodes[current]["parent_id"]
        assert [r["type"] for r in chain] == ["class", "major", "department", "college", "school"]
        assert chain[1]["name"] == CLASS_MAJORS[class_id]
        assert chain[2]["id"] == LEGACY[class_id][1]
        assert chain[3]["id"] == LEGACY[chain[2]["id"]][1]
        assert nodes[class_id]["entry_year"] == (2017 if class_id in (9, 12) else 2016)
    assert all(r["organization_id"] in classes for r in data["memberships"])
    primary = Counter(r["user_id"] for r in data["memberships"] if r["is_primary"])
    assert all(n == 1 for n in primary.values()), "Duplicate primary memberships"
    if before:
        for table, old_rows in before.items():
            if table == "organizations":
                assert len(data[table]) - len(old_rows) in (0, 4)
                continue
            fields = TEXT_FIELDS.get(table, set())
            def invariant(rows):
                return sorted(json.dumps({k: v for k, v in row.items() if k not in fields}, default=str, sort_keys=True) for row in rows)
            assert invariant(old_rows) == invariant(data[table]), f"Protected data changed: {table}"
    return {"users": len(data["users"]), "memberships": len(data["memberships"]),
            "organizations": len(nodes), "classes": len(classes), "majors": 4}


def run(args, convert):
    url = os.environ["CAMPUS_MAINTENANCE_DATABASE_URL"]
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    engine = create_engine(url, hide_parameters=True, connect_args={"connect_timeout": 12})
    with engine.connect().execution_options(isolation_level="SERIALIZABLE") as conn:
        with conn.begin():
            if not args.apply:
                conn.execute(text("SET TRANSACTION READ ONLY"))
            conn.execute(text("SET LOCAL lock_timeout='5s'"))
            conn.execute(text("SET LOCAL statement_timeout='20s'"))
            meta = MetaData(schema="public")
            meta.reflect(bind=conn)
            tables = {table.name: table for table in meta.tables.values()}
            if args.apply:
                for name in sorted(tables):
                    conn.execute(text(f'LOCK TABLE "public"."{name.replace(chr(34), chr(34)*2)}" IN SHARE ROW EXCLUSIVE MODE'))
            before = snapshot(conn, tables)
            org_changes, majors = sample_changes(before["organizations"])
            changes = text_changes(before, convert)
            report = {"text_rows": dict(Counter(name for name, _, _ in changes)),
                      "organizations_to_update": org_changes, "majors_to_add": majors,
                      "counts_before": {name: len(rows) for name, rows in before.items()}}
            if not args.apply:
                print(json.dumps(report, ensure_ascii=False, default=str, indent=2))
                return
            backup_dir = Path(args.backup_dir).resolve()
            checkout = Path(__file__).resolve().parents[2]
            if backup_dir.is_relative_to(checkout):
                raise ValueError("Backup must be outside the git checkout")
            backup_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            backup = backup_dir / f"academic-cleanup-{stamp}.json"
            write_durable_json(backup, {"created_at": stamp, "data": before})
            for name, row, values in changes:
                table = tables[name]
                predicates = [column == row[column.name] for column in table.primary_key.columns]
                assert predicates, f"No primary key: {name}"
                result = conn.execute(update(table).where(*predicates).values(**values))
                assert result.rowcount == 1
            org_table = tables["organizations"]
            major_ids = {}
            for major in majors:
                node_id = conn.execute(insert(org_table).values(**major, type="major", status="active", sort_order=0).returning(org_table.c.id)).scalar_one()
                major_ids[major["name"]] = node_id
            for node_id, values in org_changes.items():
                values = dict(values)
                major_key = values.pop("major_key", None)
                if major_key:
                    values["parent_id"] = major_ids[major_key]
                result = conn.execute(update(org_table).where(org_table.c.id == node_id).values(**values))
                assert result.rowcount == 1
            after = snapshot(conn, tables)
            verified = validate(after, before)
            assert not text_changes(after, convert), "Traditional text remains in supported presentation fields"
            receipt = {"backup": str(backup), "backup_sha256": hashlib.sha256(backup.read_bytes()).hexdigest(),
                       "changes": report, "major_ids": major_ids, "verified": verified}
            receipt_path = backup.with_suffix(".receipt.json")
            write_durable_json(receipt_path, receipt)
        print(json.dumps({"committed": True, "receipt": str(receipt_path), **verified}, ensure_ascii=False))
    engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backup-dir")
    args = parser.parse_args()
    if args.apply and not args.backup_dir:
        parser.error("--apply requires --backup-dir")
    from opencc import OpenCC
    run(args, OpenCC("t2s").convert)
