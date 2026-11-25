import copy

from conftest import post
from guided_notes.db import connection
from test_export_previews import create, ended_activity
def confirm_export(client, pid, *, key="request-1", overwrite=None, **extra):
    csrf = client.get("/csrf").json["csrf"]
    return client.post(f"/teacher/notes/export-previews/{pid}/confirm",
        json={"confirm": True, "overwrite_item_ids": overwrite or [], **extra},
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": key})


def setup_preview(app, teacher, writable):
    aid, catalog, snapshot = ended_activity(app, teacher)
    response = create(teacher, aid)
    assert response.status_code == 201
    return response.json, catalog, snapshot


def test_confirm_writes_one_batch_per_unit_and_verifies_literals(app, teacher, writable):
    preview, _, _ = setup_preview(app, teacher, writable)
    response = confirm_export(teacher, preview["preview_id"])
    assert response.status_code == 200, response.get_data(as_text=True)
    report = response.json
    assert report["status"] == "completed"
    assert report["counts"]["verified"] == 3
    assert [len(batch) for batch in writable.writes] == [2, 1]
    assert all(w.text == "  =001\n中文  " for b in writable.writes for w in b)
    assert all(i["verified_at"] for u in report["units"] for i in u["items"])
    assert {u["winner_group_id"] for u in report["units"]} == {"group-A"}
    writes = len(writable.writes)
    again = confirm_export(teacher, preview["preview_id"])
    assert again.json == report and len(writable.writes) == writes
    assert teacher.get(f"/teacher/notes/operations/{report['operation_id']}", headers={"Accept": "application/json"}).json == report
    assert "回填報告" in teacher.get(f"/teacher/notes/operations/{report['operation_id']}").get_data(as_text=True)


def test_idempotency_payload_conflict_and_consumed_preview(app, teacher, writable):
    preview, _, _ = setup_preview(app, teacher, writable)
    assert confirm_export(teacher, preview["preview_id"]).status_code == 200
    assert confirm_export(teacher, preview["preview_id"], overwrite=["extra"]).status_code == 409
    assert confirm_export(teacher, preview["preview_id"], key="other-key").status_code == 409
    assert len(writable.writes) == 2


def test_source_and_result_changes_reject_before_writing(app, teacher, writable):
    preview, _, snapshot = setup_preview(app, teacher, writable)
    writable.put(4, 6, {"stringValue": "external"})
    response = confirm_export(teacher, preview["preview_id"])
    assert response.status_code == 409
    assert response.json["error"]["code"] == "PREVIEW_STALE"
    assert not writable.writes
    fresh = create(teacher, snapshot["activity_id"]).json
    snapshot["result_version"] = "changed"
    assert confirm_export(teacher, fresh["preview_id"], key="new").status_code == 409
    assert not writable.writes


def test_overwrite_requires_exact_explicit_set(app, teacher, writable):
    aid, _, _ = ended_activity(app, teacher)
    writable.put(4, 6, {"formulaValue": "=1+1"})
    preview = create(teacher, aid).json
    assert confirm_export(teacher, preview["preview_id"]).status_code == 409
    assert not writable.writes
    required = [i["item_id"] for i in preview["items"] if i["action"] == "requires_overwrite_confirmation"]
    assert confirm_export(teacher, preview["preview_id"] , key="correct", overwrite=required).json["status"] == "completed"


def test_no_winner_and_same_text_do_not_send_writes(app, teacher, writable):
    aid, _, snapshot = ended_activity(app, teacher)
    for unit in snapshot["units"]:
        unit.update(no_winner=True, winner_group_id=None, answers=[])
    preview = create(teacher, aid).json
    report = confirm_export(teacher, preview["preview_id"]).json
    assert report["status"] == "completed" and report["counts"]["skipped"] == 3
    assert not writable.writes


def test_unknown_with_successful_readback_is_verified(app, teacher, writable):
    preview, _, _ = setup_preview(app, teacher, writable)
    writable.fail_at, writable.unknown_applies = 1, True
    report = confirm_export(teacher, preview["preview_id"]).json
    assert report["status"] == "completed"
    assert report["counts"]["verified"] == 3
    assert len(writable.writes) == 2


def test_last_uncertain_request_with_matching_readback_clears_transient_error(app, teacher, writable):
    preview, _, _ = setup_preview(app, teacher, writable)
    writable.fail_at, writable.unknown_applies = 2, True
    report = confirm_export(teacher, preview["preview_id"]).json
    assert report["status"] == "completed"
    assert report["error_code"] is None


def test_readback_failure_is_unknown_and_later_units_not_processed(app, teacher, writable):
    preview, _, _ = setup_preview(app, teacher, writable)
    # Enable after the initial freshness reads, immediately when writing.
    writable.write_hook = lambda: setattr(writable, "readback_error", True)
    report = confirm_export(teacher, preview["preview_id"]).json
    assert report["status"] == "needs_attention"
    assert report["counts"]["unknown"] == 2
    assert report["counts"]["not_processed"] == 1
    assert len(writable.writes) == 1


def test_confirm_authorization_csrf_and_client_targets(app, teacher, writable):
    preview, _, _ = setup_preview(app, teacher, writable)
    pid = preview["preview_id"]
    other = app.test_client()
    assert confirm_export(other, pid).status_code == 401
    assert post(other, "/teacher/session", username="other", password="test-password").status_code == 204
    assert confirm_export(other, pid).status_code == 404
    assert teacher.post(f"/teacher/notes/export-previews/{pid}/confirm", json={"confirm": True}).status_code == 403
    assert confirm_export(teacher, pid, snapshot={}).status_code == 400
    assert not writable.writes


def test_report_and_recovery_ownership_are_checked(app, teacher, writable):
    preview, _, _ = setup_preview(app, teacher, writable)
    report = confirm_export(teacher, preview["preview_id"]).json
    other = app.test_client()
    post(other, "/teacher/session", username="other", password="test-password")
    url = f"/teacher/notes/operations/{report['operation_id']}"
    before = len(writable.calls), len(writable.writes)
    assert other.get(url).status_code == 404
    assert post(other, url + "/recovery-preview").status_code == 404
    assert teacher.get("/teacher/notes/operations/unknown").status_code == 404
    assert (len(writable.calls), len(writable.writes)) == before


def test_matching_values_and_non_target_cells_remain_unchanged(app, teacher, writable):
    aid, catalog, snapshot = ended_activity(app, teacher)
    writable.put(4, 6, {"stringValue": "  =001\n中文  "})
    before = copy.deepcopy(writable.sheet)
    preview = create(teacher, aid).json
    report = confirm_export(teacher, preview["preview_id"]).json
    assert report["status"] == "completed"
    assert [len(b) for b in writable.writes] == [1, 1]
    assert writable.sheet["merges"] == before["merges"]
    targets = {(5, 6), (7, 5)}
    for row, data in enumerate(before["data"][0]["rowData"]):
        for col, cell in enumerate(data.get("values", [])):
            if (row, col) not in targets:
                assert writable.sheet["data"][0]["rowData"][row]["values"][col] == cell


def test_result_change_during_last_source_read_prevents_write(app, teacher, writable, monkeypatch):
    preview, _, snapshot = setup_preview(app, teacher, writable)
    read = writable.read_sheet
    count = 0
    def change(*args):
        nonlocal count
        result = read(*args)
        count += 1
        if count == 2:
            snapshot["units"][0]["answers"][0]["answer_text"] = "changed"
        return result
    monkeypatch.setattr(writable, "read_sheet", change)
    assert confirm_export(teacher, preview["preview_id"]).status_code == 409
    assert not writable.writes


def test_html_confirmation_uses_server_preview_and_redirects(app, teacher, writable):
    preview, _, _ = setup_preview(app, teacher, writable)
    pid = preview["preview_id"]
    token = teacher.get("/csrf").json["csrf"]
    response = teacher.post(f"/teacher/notes/export-previews/{pid}/confirm",
        data={"csrf_token": token, "confirm": "true", "idempotency_key": "html-request"})
    assert response.status_code == 303
    assert "回填報告" in teacher.get(response.location).get_data(as_text=True)
