def test_student_join_and_room_are_separate_private_shells(classroom_app):
    client = classroom_app.test_client()
    join = client.get('/student')
    assert join.status_code == 200
    assert b'id="join"' in join.data and b'id="questions"' not in join.data
    room = client.get('/student/classrooms/original-room')
    assert room.status_code == 200
    assert b'id="join"' not in room.data
    assert b'data-classroom-id="original-room"' in room.data
    assert b'id="closed-notice"' in room.data
    assert b'id="questions"' in room.data
    assert b'localStorage' not in room.data
    assert join.headers['Cache-Control'] == room.headers['Cache-Control'] == 'no-store'


def test_student_shell_never_server_renders_classroom_content(classroom_app):
    response = classroom_app.test_client().get('/student/classrooms/not-authorized')
    assert b'<li>' not in response.data
    assert b'id="results"' in response.data
