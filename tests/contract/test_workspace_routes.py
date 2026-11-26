from google_support import google_app, google_teacher, post, login


def test_workspace_auth_and_welcome(google_app, google_teacher):
    assert google_app.test_client().get('/teacher/workspace').status_code == 303
    page = google_teacher.get('/teacher')
    assert '進入我的課程' in page.text
    assert 'id="create-activity"' not in page.text
    assert not google_app.config['GOOGLE_PROVIDER'].calls[-1][0] == 'authorize'


def test_courses_and_course_navigation(google_app, google_teacher):
    c = post(google_teacher, '/teacher/courses', title='計算機概論').json['course_id']
    root = '/teacher/workspace/courses/' + c
    assert '計算機概論' in google_teacher.get('/teacher/workspace').text
    for suffix in ('', '/lectures', '/classrooms'):
        page = google_teacher.get(root + suffix)
        assert page.status_code == 200
        assert '計算機概論' in page.text
        assert '課程總覽' in page.text
    assert google_teacher.get('/teacher/courses').is_json
    other = login(google_app.test_client(), google_app, 'B')
    assert other.get(root).status_code == 404


def test_classroom_context_is_fixed(google_teacher):
    c = post(google_teacher, '/teacher/courses', title='A').json['course_id']
    room = post(google_teacher, f'/teacher/courses/{c}/classrooms', title='上午班').json
    url = f'/teacher/workspace/courses/{c}/classrooms/' + room['classroom_id']
    page = google_teacher.get(url)
    assert page.status_code == 200
    assert room['code'] in page.text
    assert 'data-classroom-id="' + room['classroom_id'] + '"' in page.text
    c2 = post(google_teacher, '/teacher/courses', title='B').json['course_id']
    assert google_teacher.get(url.replace(c, c2)).status_code == 404


def test_teacher_group_list_is_private_and_live(google_app,google_teacher):
    c=post(google_teacher,'/teacher/courses',title='Group list').json['course_id']
    room=post(google_teacher,f'/teacher/courses/{c}/classrooms',title='今日').json
    route=f"/teacher/workspace/courses/{c}/classrooms/{room['classroom_id']}/groups"
    student=google_app.test_client()
    assert post(student,'/classroom-memberships',code=room['code'],group_name='<script>甲</script>').status_code==201
    assert student.get(route,headers={'Accept':'application/json'}).status_code==401
    result=google_teacher.get(route).json
    assert result['groups'][0]['name']=='<script>甲</script>'
    assert set(result['groups'][0])=={'group_id','name'}
