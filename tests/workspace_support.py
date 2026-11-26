import copy
import json
from pathlib import Path
import pytest
from google_support import google_app, google_teacher, post
from guided_notes.db import connection


class Sheets:
    def __init__(self):
        self.layout=json.loads((Path(__file__).parent/'fixtures/sheets_layouts.json').read_text(encoding='utf-8'))['mixed']
        self.calls=[]
        self.hook=None
    def list_worksheets(self, sid):
        assert not connection().in_transaction
        self.calls.append('list')
        if self.hook:self.hook()
        return [{'sheet_id':7,'title':'學習單'}]
    def read_sheet(self,sid,gid):
        assert not connection().in_transaction
        self.calls.append('read')
        if self.hook:self.hook()
        return copy.deepcopy(self.layout)


@pytest.fixture
def flow(google_app,google_teacher):
    google_app.config['NOTES_GATEWAY']=Sheets()
    c=post(google_teacher,'/teacher/courses',title='測試課程').json['course_id']
    response=post(google_teacher,f'/teacher/workspace/courses/{c}/imports',source_kind='link',spreadsheet_url='https://docs.google.com/spreadsheets/d/synthetic/edit#gid=7')
    assert response.status_code==201,response.text
    return response.json['flow_id']


def path(flow, action=''):
    return '/teacher/workspace/imports/'+flow+('/'+action if action else '')



def published(teacher,fid):
    post(teacher,path(fid,'read'))
    pid=post(teacher,path(fid,'previews'),choice_revision=1,sheet_id=7,name_mode='source').json['preview_id']
    response=post(teacher,path(fid,'confirm'),confirm=True,preview_id=pid)
    assert response.status_code==200,response.text
    return response.json['catalog'],pid
