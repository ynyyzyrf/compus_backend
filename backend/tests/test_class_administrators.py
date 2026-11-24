import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.deps import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.enums import Role, Status
from app.models.organization import ClassAdministrator, Membership
from app.models.user import User


@pytest.fixture()
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as value:
        yield value
    app.dependency_overrides.clear()


def auth(user):
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role, user.auth_version)}"}


def assignment_url(class_id):
    return f"/api/v1/admin/organizations/{class_id}/class-admins"


def applicant(db, class_id, name):
    user = User(name=name, role=Role.USER, status=Status.ACTIVE, pending_class_id=class_id)
    db.add(user)
    db.flush()
    return user


def test_only_super_admin_can_manage_class_administrators(ctx, client):
    reviewer = ctx.user("張晨")
    class_id = ctx.class_id_for("張晨")
    url = assignment_url(class_id)
    assert client.post(url, headers=auth(reviewer), json={"user_id": reviewer.id}).status_code == 403
    super_auth = auth(ctx.user("MAG"))
    assert client.post(url, headers=super_auth, json={"user_id": reviewer.id}).status_code == 200
    assert reviewer.role == Role.CLASS_ADMIN
    for method, path, body in [
        ("get", url, None),
        ("post", url, {"user_id": ctx.user("黃俊傑").id}),
        ("delete", f"{url}/{reviewer.id}", None),
        ("get", f"/api/v1/admin/organizations/{class_id}/class-admin-candidates", None),
    ]:
        kwargs = {"headers": auth(reviewer)}
        if body is not None:
            kwargs["json"] = body
        assert getattr(client, method)(path, **kwargs).status_code == 403
    for path in ["/api/v1/admin/dashboard", "/api/v1/admin/members", "/api/v1/admin/organizations",
                 "/api/v1/admin/directory-permissions", "/api/v1/admin/missing-classes"]:
        assert client.get(path, headers=auth(reviewer)).status_code == 403


def test_multiple_administrators_only_review_their_own_class(ctx, db, client):
    class_id = ctx.class_id_for("張晨")
    other_class = ctx.class_id_for("陳思遠")
    super_auth = auth(ctx.user("MAG"))
    reviewers = [ctx.user("張晨"), ctx.user("黃俊傑")]
    for reviewer in reviewers:
        for _ in range(2):
            assert client.post(assignment_url(class_id), headers=super_auth, json={"user_id": reviewer.id}).status_code == 200
    admins = client.get(assignment_url(class_id), headers=super_auth).json()["items"]
    assert {row["id"] for row in admins} == {user.id for user in reviewers}
    own = applicant(db, class_id, "同班申请人")
    other = applicant(db, other_class, "其他班级申请人")
    for reviewer in reviewers:
        result = client.get("/api/v1/admin/affiliation-requests", headers=auth(reviewer))
        assert result.status_code == 200
        assert {row["user_id"] for row in result.json()} == {own.id}
        for action in ("approve", "reject"):
            assert client.post(f"/api/v1/admin/affiliation-requests/{other.id}/{action}", headers=auth(reviewer)).status_code == 403
    assert other.pending_class_id == other_class
    assert client.post(f"/api/v1/admin/affiliation-requests/{own.id}/approve", headers=auth(reviewers[0])).status_code == 200
    assert own.pending_class_id is None
    assert db.scalar(select(Membership.organization_id).where(Membership.user_id == own.id, Membership.is_primary.is_(True))) == class_id
    assert client.post(f"/api/v1/admin/affiliation-requests/{own.id}/approve", headers=auth(reviewers[1])).status_code == 404
    assert client.post(f"/api/v1/admin/affiliation-requests/{other.id}/reject", headers=super_auth).status_code == 200


def test_revocation_is_per_class_and_old_token_cannot_keep_review_access(ctx, db, client):
    reviewer = ctx.user("張晨")
    first = ctx.class_id_for("張晨")
    second = ctx.class_id_for("陳思遠")
    admin = auth(ctx.user("MAG"))
    for cid in (first, second):
        assert client.post(assignment_url(cid), headers=admin, json={"user_id": reviewer.id}).status_code == 200
    token_before_removal = auth(reviewer)
    user = applicant(db, first, "被撤权班级申请人")
    assert client.delete(f"{assignment_url(first)}/{reviewer.id}", headers=admin).status_code == 200
    assert reviewer.role == Role.CLASS_ADMIN
    assert client.post(f"/api/v1/admin/affiliation-requests/{user.id}/reject", headers=token_before_removal).status_code == 403
    assert client.delete(f"{assignment_url(second)}/{reviewer.id}", headers=admin).status_code == 200
    assert reviewer.role == Role.USER
    assert client.get("/api/v1/admin/affiliation-requests", headers=token_before_removal).status_code == 403


def test_invalid_assignments_are_rejected_and_candidates_are_minimal(ctx, client):
    admin = auth(ctx.user("MAG"))
    class_id = ctx.class_id_for("張晨")
    school = ctx.org_by_name("XX校友組織", None).id
    assert client.post(assignment_url(school), headers=admin, json={"user_id": ctx.user("張晨").id}).status_code == 404
    assert client.post(assignment_url(class_id), headers=admin, json={"user_id": 999999}).status_code == 400
    assert client.post(assignment_url(class_id), headers=admin, json={"user_id": ctx.user("MAG").id}).status_code == 400
    reviewer = ctx.user("張晨")
    client.post(assignment_url(class_id), headers=admin, json={"user_id": reviewer.id})
    result = client.get(f"/api/v1/admin/organizations/{class_id}/class-admin-candidates?page_size=2", headers=admin).json()
    assert result["total"] == 5
    assert len(result["items"]) == 2
    assert all(set(item) == {"id", "name", "org_path"} for item in result["items"])
    assert reviewer.id not in {item["id"] for item in result["items"]}


def test_disabled_class_has_no_review_authority(ctx, db, client):
    reviewer = ctx.user("張晨")
    class_id = ctx.class_id_for("張晨")
    admin = auth(ctx.user("MAG"))
    client.post(assignment_url(class_id), headers=admin, json={"user_id": reviewer.id})
    pending = applicant(db, class_id, "停用班级申请人")
    assert client.put(f"/api/v1/admin/organizations/{class_id}", headers=admin, json={"status": "disabled"}).status_code == 200
    assert client.get("/api/v1/admin/affiliation-requests", headers=auth(reviewer)).json() == []
    assert client.post(f"/api/v1/admin/affiliation-requests/{pending.id}/approve", headers=auth(reviewer)).status_code == 403


def test_general_member_editor_cannot_create_unscoped_class_admin(ctx, db, client):
    reviewer = ctx.user("張晨")
    admin = auth(ctx.user("MAG"))
    member_url = f"/api/v1/admin/members/{reviewer.id}"
    assert client.put(member_url, headers=admin, json={"role": "class_admin"}).status_code == 400
    cid = ctx.class_id_for("張晨")
    client.post(assignment_url(cid), headers=admin, json={"user_id": reviewer.id})
    assert client.put(member_url, headers=admin, json={"role": "class_admin", "name": reviewer.name}).status_code == 200
    assert client.put(member_url, headers=admin, json={"role": "user"}).status_code == 200
    assert db.get(ClassAdministrator, (cid, reviewer.id)) is None
    assert client.get("/api/v1/admin/affiliation-requests", headers=auth(reviewer)).status_code == 403
