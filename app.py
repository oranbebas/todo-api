"""
Features
- Base URL is "http://localhost:5000/todo/api/vi/tasks".
- Request and Response format is JSON.
- Authorization is done by user. (curl -u [id]:[pass] ...)
- Relationship is made, but it's not sure exactly made. (e.g. can't delete task, raise error.)
- DB is MySQL.

Request example
- curl -i -u miguel:python http://localhost:5000/todo/api/v1/tasks -X GET
- curl -i -u miguel:python http://localhost:5000/todo/api/v1/tasks/1 -X GET
- curl -i -u miguel:python -H "Content-Type:application/json" http://localhost:5000/todo/api/v1/tasks -X POST -d '{"title":"test1"}'
- curl -i -u miguel:python -H "Content-Type:application/json" http://localhost:5000/todo/api/v1/tasks/1 -X PUT -d '{"title":"test1"}'
- curl -i -u miguel:python http://localhost:5000/todo/api/v1/tasks/1 -X DELETE

Additional todo
- Custmize GET request for "tasks", for example pagination, filtering by URL.
- Error handling. (e.g. input format.)
"""

from flask import Flask, jsonify, abort, make_response, request, url_for
from flask_httpauth import HTTPBasicAuth
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@localhost/tutorial'
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tutorial.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
auth = HTTPBasicAuth()


@auth.get_password
def get_password(username):
    users = User.query.all()
    for user in users:
        if user.login_id == username:
            return user.password
    return None


@auth.error_handler
def unauthorized():
    return make_response(jsonify({'error': 'Unauthorized access'}, 401))


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    login_id = db.Column(db.String(20), unique=True)
    password = db.Column(db.String(20))
    task = db.relationship('Task', backref='user', lazy='dynamic')

    def __init__(self, login_id="", password=""):
        self.login_id = login_id
        self.password = password

    def __repr__(self):
        return '<User login_id:{}, password:{}>'.format(self.login_id, self.password)


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    description = db.Column(db.Text)
    done = db.Column(db.Boolean)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


    def __init__(self, title="", description="", done="", user_id=""):
        self.title = title
        self.description = description
        self.done = done
        self.user_id = user_id

    def __repr__(self):
        #return '<Task id:{}, title:{}, description:{}, done:{}>'.format(self.id, self.title, self.description, self.done)
        return self.__dict__.pop("_sa_instance_state")


def model2dict(model):
    if "_sa_instance_state" in model.__dict__.keys():
        model.__dict__.pop("_sa_instance_state")
    return model.__dict__


@app.route('/todo/api/v1/users', methods=['GET'])
@auth.login_required
def get_users():
    users = [model2dict(user) for user in User.query.all()]
    return jsonify({'users': users})


@app.route('/todo/api/v1/users/<int:user_id>', methods=['GET'])
@auth.login_required
def get_user(user_id):
    # レコード参照
    user = User.query.get(user_id)
    if not user:
        abort(404)
    return jsonify({'users': model2dict(user)})


@app.route('/todo/api/v1/users', methods=['POST'])
@auth.login_required
def create_user():
    # リクエストチェック -JSONかつlogin_id, password含む
    if not request.is_json or 'login_id' not in request.get_json() or 'password' not in request.get_json():
        abort(400)

    # レコード作成
    user = User(request.get_json()['login_id'], request.get_json()['password'])
    db.session.add(user)
    db.session.commit()
    print(user) # これがないとレスポンスボディのuser中身が表示されない

    return jsonify({'users': model2dict(user)}), 201


@app.route('/todo/api/v1/users/<int:user_id>', methods=['PUT'])
@auth.login_required
def update_user(user_id):
    # リクエストチェック
    if not request.is_json:
        abort(400)

    # レコード参照
    user = User.query.get(user_id)
    if not user:
        abort(404)

    # 送信項目ごとの形式チェック
    if 'login_id' in request.get_json() and type(request.get_json()['login_id']) != str:
        abort(400)
    if 'password' in request.get_json() and type(request.get_json()['password']) != str:
        abort(400)

    # レコード更新
    if 'login_id' in request.get_json():
        user.login_id = request.get_json()['login_id']
    if 'password' in request.get_json():
        user.password = request.get_json()['password']
    db.session.commit()

    return jsonify({'users': model2dict(user)})


@app.route('/todo/api/v1/users/<int:user_id>', methods=['DELETE'])
@auth.login_required
def delete_user(user_id):
    # レコード参照
    user = User.query.get(user_id)
    if not user:
        abort(404)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'result': True})


@app.route('/todo/api/v1/tasks', methods=['GET'])
@auth.login_required
def get_tasks():
    # レコード参照
    user = User.query.filter_by(login_id=auth.username()).first()
    tasks = [model2dict(task) for task in Task.query.filter_by(user_id=user.id)]
    return jsonify({'tasks': [make_public_task(task) for task in tasks]})

@app.route('/todo/api/v1/tasks/<int:task_id>', methods=['GET'])
@auth.login_required
def get_task(task_id):
    # レコード参照
    user = User.query.filter_by(login_id=auth.username()).first()
    task = Task.query.filter_by(id=task_id, user_id=user.id).first()
    if not task:
        abort(404)
    return jsonify({'tasks': make_public_task(model2dict(task))})


@app.route('/todo/api/v1/tasks', methods=['POST'])
@auth.login_required
def create_task():
    # リクエストチェック -JSONかつtitle含む
    if not request.is_json or 'title' not in request.get_json():
        abort(400)

    # レコード参照
    user = User.query.filter_by(login_id=auth.username()).first()

    # descriptionがあれば代入
    if 'description' in request.get_json():
        description = request.get_json()['description']
    else:
        description = ''

    # レコード作成
    task = Task(request.get_json()['title'], description, False, user.id)
    db.session.add(task)
    db.session.commit()

    return jsonify({'task': make_public_task(model2dict(task))}), 201


@app.route('/todo/api/v1/tasks/<int:task_id>', methods=['PUT'])
@auth.login_required
def update_task(task_id):
    # リクエストチェック
    if not request.is_json:
        abort(400)

    # レコード参照
    user = User.query.filter_by(login_id=auth.username()).first()
    task = Task.query.filter_by(id=task_id, user_id=user.id).first()
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
    db.session.commit()

    return jsonify({'task': make_public_task(model2dict(task))})


@app.route('/todo/api/v1/tasks/<int:task_id>', methods=['DELETE'])
@auth.login_required
def delete_task(task_id):
    # レコード参照
    user = User.query.filter_by(login_id=auth.username()).first()
    task = Task.query.filter_by(id=task_id, user_id=user.id)
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
