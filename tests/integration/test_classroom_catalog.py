from catalog_support import course_import_id
from conftest import post


def test_same_teacher_cannot_cross_catalogs(classroom_app, classroom_teacher, classroom_setup):
    course, room = classroom_setup
    second = post(classroom_teacher, "/teacher/courses", title="另一門課").json
    path = f"/teacher/classrooms/{room['classroom_id']}/activities"
    response = post(classroom_teacher, path, import_id=course_import_id(second["course_id"]), import_version=1)
    assert response.status_code == 404
    assert response.json["error"] == "CATALOG_NOT_FOUND"
    assert classroom_teacher.get(path).json == {"activities": []}
    assert post(classroom_teacher, path, import_id=course_import_id(course["course_id"]), import_version=2).status_code == 201
    assert classroom_teacher.get(path).json["activities"][0]["import_version"] == 2
    classroom_app.config["GET_COURSE_CATALOG"] = None
    # 001 now exists: clearing the test override uses the real scoped provider.
    assert post(classroom_teacher, path, import_id=course_import_id(course["course_id"]), import_version=1).status_code == 404
    # An explicitly unavailable provider must still fail closed.
    classroom_app.config["GET_COURSE_CATALOG"] = False
    assert post(classroom_teacher, path, import_id=course_import_id(course["course_id"]), import_version=1).status_code == 503
