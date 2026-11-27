"""Test clients and requests for the 012 student tab protocol."""
from http.cookies import SimpleCookie
from uuid import uuid4

from conftest import post


def browser_tabs(app):
    first = app.test_client()
    initial = first.get('/student')
    assert initial.status_code == 200
    second = app.test_client()
    for header in initial.headers.getlist('Set-Cookie'):
        for cookie in SimpleCookie(header).values():
            second.set_cookie(cookie.key, cookie.value, path=cookie['path'] or '/')
    return first, second


def join_tab(client, room, group):
    return post(client, '/classroom-memberships', code=room['code'], group_name=group,
                page_protocol=1, page_id=uuid4().hex, request_id=uuid4().hex)


def activate_tab(client, joined):
    assert joined.status_code == 201, joined.json
    data = joined.json
    assert data.get('resume_id'), 'Join must return a tab-scoped recovery index'
    response = post(client, f"/classrooms/{data['classroom_id']}/tab-access",
                    resume_id=data['resume_id'], page_id=uuid4().hex, request_id=uuid4().hex)
    assert response.status_code == 200, response.json
    return {'X-Classroom-Tab': response.json['page_token']}
