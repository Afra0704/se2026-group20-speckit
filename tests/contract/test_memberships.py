from conftest import post


def test_membership_and_browser_recovery(app, teacher, activity):
    first, second, outsider = (app.test_client() for _ in range(3))
    url = f"/activities/{activity['activity_id']}"
    code = activity["code"]
    assert post(first, "/activity-memberships", code=code, group_name=" ").status_code == 400
    a = post(first, "/activity-memberships", code=code, group_name=" A ").json
    b = post(second, "/activity-memberships", code=code, group_name="A").json
    assert a["group_id"] == b["group_id"]
    assert len(a["questions"]) == 3
    assert post(first, url + "/start").status_code == 403
    post(teacher, url + "/start")
    post(teacher, url + "/close")
    assert post(outsider, "/activity-memberships", code=code, group_name="A").status_code == 409
    assert post(outsider, url + "/result-access").status_code == 403
    first.delete_cookie("session")
    assert post(first, url + "/result-access", group_name="other").status_code == 400
    assert post(first, url + "/result-access").status_code == 204
    assert first.get(url + "/state").json["group_name"] == "A"
    assert post(first, url + "/submissions", question_id="q1", items=[]).status_code == 403
