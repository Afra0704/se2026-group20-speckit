import copy
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest

from conftest import post
from guided_notes import create_app
from guided_notes.db import connection
from test_export_previews import create
from test_export_routes import confirm_export, setup_preview


def recover(teacher, operation_id):
    return post(teacher, f"/teacher/notes/operations/{operation_id}/recovery-preview")


def test_recovery_distinguishes_consented_overwrite_from_new_conflict(app, teacher, writable):
    from test_export_previews import ended_activity
    aid, _, _ = ended_activity(app, teacher)
    writable.put(7, 5, {'stringValue': 'original-third-answer'})
    preview = create(teacher, aid).json
    required = [i['item_id'] for i in preview['items'] if i['action'] == 'requires_overwrite_confirmation']
    assert required
    writable.fail_at = 2
    first = confirm_export(teacher, preview['preview_id'], overwrite=required).json
    fresh = recover(teacher, first['operation_id']).json
    page = teacher.get(fresh['preview_url']).text
    assert '待覆寫（沿用前次同意，原內容未變）' in page
    assert fresh['counts']['requires_overwrite_confirmation'] == 0
    assert 'name="overwrite_item_ids"' not in page
    # A later source edit needs new consent and must not inherit the old one.
    writable.put(7, 5, {'stringValue': 'new-external-answer'})
    conflict = recover(teacher, first['operation_id']).json
    page = teacher.get(conflict['preview_url']).text
    assert '需要覆寫確認' in page and 'name="overwrite_item_ids"' in page
    assert '待覆寫（沿用前次同意，原內容未變）' not in page
    assert confirm_export(teacher, conflict['preview_id'], key='missing-consent').status_code == 409


def test_partial_failure_recovers_only_pending_set_and_preserves_winner(app, teacher, writable):
    preview, _, _ = setup_preview(app, teacher, writable)
    writable.fail_at = 2
    first = confirm_export(teacher, preview["preview_id"]).json
    assert first["counts"]["verified"] == 2 and first["counts"]["failed"] == 1
    recovery = recover(teacher, first["operation_id"])
    assert recovery.status_code == 201
    assert recovery.json["origin_operation_id"] == first["operation_id"]
    assert [i["action"] for i in recovery.json["items"]] == ["already_matches", "already_matches", "write"]
    second = confirm_export(teacher, recovery.json["preview_id"], key="recovery").json
    assert second["status"] == "completed"
    assert [len(batch) for batch in writable.writes] == [2, 1, 1]
    assert second["origin_operation_id"] == first["operation_id"]
    assert {u["winner_group_id"] for u in second["units"]} == {"group-A"}


def test_recovery_reads_first_and_retains_conflicts_for_new_confirmation(app, teacher, writable):
    preview, _, _ = setup_preview(app, teacher, writable)
    writable.fail_at = 1
    first = confirm_export(teacher, preview["preview_id"]).json
    writable.put(4, 6, {"stringValue": "external-conflict"})
    pending = recover(teacher, first["operation_id"]).json
    assert pending["items"][0]["action"] == "requires_overwrite_confirmation"
    report = teacher.get(f"/teacher/notes/operations/{first['operation_id']}", headers={"Accept": "application/json"}).json
    assert report["counts"]["conflict"] == 1
    assert confirm_export(teacher, pending["preview_id"], key="recover-missing").status_code == 409
    required = [i["item_id"] for i in pending["items"] if i["action"] == "requires_overwrite_confirmation"]
    assert confirm_export(teacher, pending["preview_id"], key="recover-explicit", overwrite=required).json["status"] == "completed"


def test_unknown_success_recovery_verifies_without_rewriting(app, teacher, writable):
    preview, _, _ = setup_preview(app, teacher, writable)
    writable.write_hook = lambda: setattr(writable, "readback_error", True)
    first = confirm_export(teacher, preview["preview_id"]).json
    writable.write_hook = None
    fresh = recover(teacher, first["operation_id"]).json
    assert fresh["counts"]["already_matches"] == 2
    assert confirm_export(teacher, fresh["preview_id"], key="recover").json["status"] == "completed"
    assert [len(batch) for batch in writable.writes] == [2, 1]


@pytest.mark.parametrize("change", ["version", "winner"])
def test_changed_result_version_blocks_recovery_without_google_write(app, teacher, writable, change):
    preview, _, snapshot = setup_preview(app, teacher, writable)
    writable.fail_at = 1
    first = confirm_export(teacher, preview["preview_id"]).json
    if change == "version":
        snapshot["result_version"] = "different"
    else:
        snapshot["units"][0]["winner_group_id"] = "other-winner"
    before = len(writable.writes)
    assert recover(teacher, first["operation_id"]).status_code == 409
    assert len(writable.writes) == before


def test_expired_lease_fences_writer_and_recovery_does_not_resend_verified(app, teacher, writable):
    preview, _, _ = setup_preview(app, teacher, writable)
    def expire():
        connection().execute("UPDATE notes_source_leases SET expires_at=0")
    writable.write_hook = expire
    response = confirm_export(teacher, preview["preview_id"])
    assert response.status_code == 409
    assert len(writable.writes) == 1
    writable.write_hook = None
    with app.app_context():
        oid = connection().execute("SELECT operation_id FROM notes_write_operations").fetchone()[0]
    report = teacher.get(f"/teacher/notes/operations/{oid}", headers={"Accept": "application/json"}).json
    assert report["status"] == "recovering"
    recovery = recover(teacher, oid).json
    assert confirm_export(teacher, recovery["preview_id"], key="recovery").json["status"] == "completed"
    assert [len(batch) for batch in writable.writes] == [2, 1]


def test_restart_keeps_unknown_and_requires_recovery(app, teacher, writable):
    preview, _, _ = setup_preview(app, teacher, writable)
    class Crash(BaseException):
        pass
    writable.write_hook = lambda: (_ for _ in ()).throw(Crash())
    with pytest.raises(Crash):
        confirm_export(teacher, preview["preview_id"])
    writable.write_hook = None
    restarted = create_app({"TESTING": True, "TEACHER_AUTH_MODE": "test_password", "SECRET_KEY": app.secret_key, "DATABASE": app.config["DATABASE"],
        "NOTES_GATEWAY": writable, "GET_SETTLED_RESULTS": app.config["GET_SETTLED_RESULTS"]})
    client = restarted.test_client()
    post(client, "/teacher/session", username="teacher", password="test-password")
    replay = confirm_export(client, preview["preview_id"])
    assert replay.json["status"] == "recovering"
    assert len(writable.writes) == 1  # no automatic retransmission on replay
    pending = recover(client, replay.json["operation_id"]).json
    assert confirm_export(client, pending["preview_id"], key="after-restart").json["status"] == "completed"


def test_same_key_running_returns_202_other_source_attempt_is_busy(app, teacher, writable):
    preview, _, snapshot = setup_preview(app, teacher, writable)
    other_preview = create(teacher, snapshot["activity_id"]).json
    client = app.test_client()
    with teacher.session_transaction() as state:
        saved = dict(state)
    with client.session_transaction() as state:
        state.update(saved)
    entered, release = Event(), Event()
    def block():
        entered.set()
        assert release.wait(10)
    writable.write_hook = block
    with ThreadPoolExecutor(1) as pool:
        future = pool.submit(confirm_export, client, preview["preview_id"])
        try:
            assert entered.wait(10)
            replay = confirm_export(teacher, preview["preview_id"])
            assert replay.status_code == 202
            assert confirm_export(teacher, other_preview["preview_id"], key="other").status_code == 409
        finally:
            release.set()
        assert future.result(timeout=10).json["status"] == "completed"


def test_moved_source_recovery_reidentifies_current_anchors(app, teacher, writable):
    preview, _, _ = setup_preview(app, teacher, writable)
    writable.fail_at = 1
    first = confirm_export(teacher, preview["preview_id"]).json
    writable.sheet = copy.deepcopy(writable.layouts["moved"])
    pending = recover(teacher, first["operation_id"]).json
    assert pending["items"][0]["answer_range"]["start_row"] == 7
    assert confirm_export(teacher, pending["preview_id"], key="moved").json["status"] == "completed"
    assert [(w.row, w.column) for w in writable.writes[1]] == [(7, 8), (8, 8)]


def test_execution_deadline_defers_without_hidden_worker(app, teacher, writable):
    preview, _, _ = setup_preview(app, teacher, writable)
    app.config["NOTES_WRITE_SECONDS"] = 0
    report = confirm_export(teacher, preview["preview_id"]).json
    assert report["status"] == "needs_attention"
    assert report["counts"]["not_processed"] == 3
    assert not writable.writes


def test_unresolved_operation_blocks_new_attempt_even_after_lease_is_released(app, teacher, writable):
    preview, _, snapshot = setup_preview(app, teacher, writable)
    writable.fail_at = 1
    first = confirm_export(teacher, preview["preview_id"]).json
    another = create(teacher, snapshot["activity_id"]).json
    assert confirm_export(teacher, another["preview_id"], key="unrelated").status_code == 409
    assert len(writable.writes) == 1
    fresh = recover(teacher, first["operation_id"]).json
    assert confirm_export(teacher, fresh["preview_id"], key="recovery").json["status"] == "completed"
    # Recovery completion unblocks the whole attempt lineage.
    current = create(teacher, snapshot["activity_id"]).json
    assert confirm_export(teacher, current["preview_id"], key="after-recovery").json["status"] == "completed"
    assert len(writable.writes) == 3


def test_physical_source_is_shared_across_different_teacher_source_records(app, teacher, writable):
    preview, _, _ = setup_preview(app, teacher, writable)
    writable.fail_at = 1
    assert confirm_export(teacher, preview["preview_id"]).json["status"] == "needs_attention"
    other = app.test_client()
    post(other, "/teacher/session", username="other", password="test-password")
    second, _, _ = setup_preview(app, other, writable)
    assert confirm_export(other, second["preview_id"], key="different-teacher").status_code == 409
    assert len(writable.writes) == 1


def test_changed_question_membership_blocks_recovery(app, teacher, writable):
    preview, _, _ = setup_preview(app, teacher, writable)
    writable.fail_at = 1
    first = confirm_export(teacher, preview["preview_id"]).json
    writable.sheet = copy.deepcopy(writable.layouts["single"])
    response = recover(teacher, first["operation_id"])
    assert response.status_code == 409
    assert response.json["error"]["code"] == "SOURCE_STRUCTURE_CHANGED"
    assert len(writable.writes) == 1


def test_timeout_without_observed_success_is_unknown_not_automatically_retried(app, teacher, writable):
    preview, _, _ = setup_preview(app, teacher, writable)
    writable.fail_at, writable.uncertain = 1, True
    report = confirm_export(teacher, preview["preview_id"]).json
    assert report["counts"]["unknown"] == 2
    assert len(writable.writes) == 1
    fresh = recover(teacher, report["operation_id"]).json
    assert confirm_export(teacher, fresh["preview_id"], key="timeout-recovery").json["status"] == "completed"
