"""
Features
- Base URL is "http://localhost:5000/todo/api/vi/tasks".
- Request and Response format is JSON.
- Authorization is needed(miguel:python).
- DB is MySQL.

Request example
- curl -i -u miguel:python http://localhost:5000/todo/api/v1/tasks -X GET
- curl -i -u miguel:python http://localhost:5000/todo/api/v1/tasks/1 -X GET
- curl -i -u miguel:python -H "Content-Type:application/json" http://localhost:5000/todo/api/v1/tasks -X POST -d '{"title":"test1"}'
- curl -i -u miguel:python -H "Content-Type:application/json" http://localhost:5000/todo/api/v1/tasks/1 -X PUT -d '{"title":"test1"}'
- curl -i -u miguel:python http://localhost:5000/todo/api/v1/tasks/1 -X DELETE

Additional todo
- For multiple users, add resource "users".
- Custmize GET request for "tasks", for example pagination, filtering by URL.
"""

from flask import Flask, jsonify, abort, make_response, request, url_for
from flask_httpauth import HTTPBasicAuth
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@localhost/tutorial'
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tutorial.db'
db = SQLAlchemy(app)
auth = HTTPBasicAuth()


@auth.get_password
def get_password(username):
    if username == 'miguel':
        return 'python'
    return None


@auth.error_handler
def unauthorized():
    return make_response(jsonify({'error': 'Unauthorized access'}, 401))


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    description = db.Column(db.Text)
    done = db.Column(db.Boolean)
    # done = db.Column(db.Integer) # For SQLite

    def __init__(self, title="", description="", done=""):
        self.title = title
        self.description = description
        self.done = done

    def __repr__(self):
        return '<Task id:{}, title:{}, description:{}, done:{}>'.format(self.id, self.title, self.description, self.done)

    def model2dict(self):
        task = {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'done': self.done
        }
        return task

tasks = []


@app.route('/todo/api/v1/tasks', methods=['GET'])
@auth.login_required
def get_tasks():
    # レコード参照
    tasks = [task.model2dict() for task in Task.query.all()]
    return jsonify({'tasks': [make_public_task(task) for task in tasks]})


@app.route('/todo/api/v1/tasks/<int:task_id>', methods=['GET'])
@auth.login_required
def get_task(task_id):
    # レコード参照
    task = Task.query.get(task_id)
    if not task:
        abort(404)
    return jsonify({'tasks': make_public_task(task.model2dict())})


@app.route('/todo/api/v1/tasks', methods=['POST'])
@auth.login_required
def create_task():
    # リクエストチェック -JSONかつtitle含む
    if not request.is_json or 'title' not in request.get_json():
        abort(400)

    # descriptionがあれば代入
    if 'description' in request.get_json():
        description = request.get_json()['description']
    else:
        description = ''

    # レコード作成
    task = Task(request.get_json()['title'], description, False)
    db.session.add(task)
    db.session.commit()


    return jsonify({'task': make_public_task(task.model2dict())}), 201


@app.route('/todo/api/v1/tasks/<int:task_id>', methods=['PUT'])
@auth.login_required
def update_task(task_id):
    # リクエストチェック
    if not request.is_json:
        abort(400)

    # レコード参照
    task = Task.query.get(task_id)
    if not task:
        abort(404)

    # 送信項目ごとの形式チェック
    if 'title' in request.get_json() and type(request.get_json()['title']) != str:
        abort(400)
    if 'description' in request.get_json() and type(request.get_json()['description']) != str:
        abort(400)
    if 'done' in request.get_json() and type(request.get_json()['done']) != bool:
        abort(400)

    # レコード更新
    if 'title' in request.get_json():
        task.title = request.get_json()['title']
    if 'description' in request.get_json():
        task.description = request.get_json()['description']
    if 'done' in request.get_json():
        task.done = request.get_json()['done']
    print(task.done)
    db.session.commit()

    return jsonify({'task': make_public_task(task.model2dict())})


@app.route('/todo/api/v1/tasks/<int:task_id>', methods=['DELETE'])
@auth.login_required
def delete_task(task_id):
    # レコード参照
    task = Task.query.get(task_id)
    if not task:
        abort(404)
    db.session.delete(task)
    db.session.commit()
    return jsonify({'result': True})


# 404エラーをJSONで返す
@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


# taskのidをuriに変更
def make_public_task(task):
    new_task = {}
    for field in task:
        if field == 'id':
            new_task['uri'] = url_for('get_task', task_id=task['id'], _external=True)
        else:
            new_task[field] = task[field]
    return new_task

if __name__ == '__main__':
    app.run(debug=True)
