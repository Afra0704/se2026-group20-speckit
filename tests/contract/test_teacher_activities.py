from conftest import post


def test_teacher_controls_lifecycle(app, teacher, activity):
    url = f"/activities/{activity['activity_id']}"
    other = app.test_client()
    assert post(other, "/teacher/session", username="other", password="test-password").status_code == 204
    assert post(other, url + "/start").status_code == 403
    assert teacher.get(url + "/state").json["phase"] == "PREPARING"
    assert post(teacher, url + "/start").json["phase"] == "LIVE"
    assert post(teacher, url + "/close").json["phase"] == "CLOSED"
    assert post(teacher, url + "/start").status_code == 409
    assert teacher.get(url + "/state").json["phase_version"] == 2


def test_csrf_required(teacher):
    assert teacher.post("/activities", json={"import_id": "demo", "import_version": 1}).status_code == 403


def test_teacher_login_survives_student_join_in_same_browser(teacher, activity):
    url = f"/activities/{activity['activity_id']}"
    joined = post(teacher, "/activity-memberships", code=activity["code"], group_name="A")
    assert joined.status_code == 201
    assert post(teacher, url + "/start").status_code == 200
    assert teacher.get(url + "/state", headers={"X-Activity-Role": "teacher"}).json["role"] == "teacher"
    assert teacher.get(url + "/state", headers={"X-Activity-Role": "student"}).json["group_name"] == "A"
