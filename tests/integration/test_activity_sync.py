from conftest import post


def test_three_clients_see_current_phase(app, teacher, activity):
    groups = [app.test_client(), app.test_client()]
    for name, client in zip(("A", "B"), groups):
        assert post(client, "/activity-memberships", code=activity["code"], group_name=name).status_code == 201
    url = f"/activities/{activity['activity_id']}"
    for version, (action, phase) in enumerate((("start", "LIVE"), ("close", "CLOSED")), 1):
        assert post(teacher, url + "/" + action).status_code == 200
        for client in (teacher, *groups):
            response = client.get(url + "/state")
            assert response.json["phase"] == phase
            assert response.json["phase_version"] == version
            assert response.headers["Cache-Control"] == "no-store"
