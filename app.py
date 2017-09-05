"""
Features
- Base URL is "http://localhost:5000/todo/api/v1".
- Request and Response format is JSON.
- Basic authentication is done by user. (curl -u [id]:[pass] ...)
- Relationship is made.
- DB is MySQL.

Request example
- token
    - curl -i -u miguel:python http://localhost:5000/todo/api/v1/token -X GET
    - curl -i -u [token]:unused http://localhost:5000/todo/api/v1/xxxx -X GET
- user
    - curl -i -u miguel:python http://localhost:5000/todo/api/v1/users -X GET
    - curl -i -u miguel:python http://localhost:5000/todo/api/v1/users/1 -X GET
    - curl -i -u miguel:python -H "Content-Type:application/json" http://localhost:5000/todo/api/v1/users -X POST -d '{"username":"miguel","password":"python"}'
    - curl -i -u miguel:python -H "Content-Type:application/json" http://localhost:5000/todo/api/v1/users/1 -X PUT -d '{"username":"Miguel"}'
    - curl -i -u miguel:python http://localhost:5000/todo/api/v1/users/1 -X DELETE
- Task
    - curl -i -u miguel:python http://localhost:5000/todo/api/v1/tasks -X GET
    - curl -i -u miguel:python http://localhost:5000/todo/api/v1/tasks/1 -X GET
    - curl -i -u miguel:python -H "Content-Type:application/json" http://localhost:5000/todo/api/v1/tasks -X POST -d '{"title":"test1"}'
    - curl -i -u miguel:python -H "Content-Type:application/json" http://localhost:5000/todo/api/v1/tasks/1 -X PUT -d '{"title":"test1"}'
    - curl -i -u miguel:python http://localhost:5000/todo/api/v1/tasks/1 -X DELETE

Additional todo
- Custmize GET request for "tasks", for example pagination, filtering by URL.
- Error handling. (e.g. input format.)
"""

from flask import Flask, jsonify, abort, make_response, request, url_for, g
from flask_httpauth import HTTPBasicAuth
from flask_sqlalchemy import SQLAlchemy
from passlib.apps import custom_app_context as pwd_context
from itsdangerous import(TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'the quick brown fox jumps over the lazy dog'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@localhost/tutorial'
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tutorial.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
auth = HTTPBasicAuth()


@auth.verify_password
def verify_password(username_or_token, password):
    # first try to authenticate by token
    user = User.verify_auth_token(username_or_token)
    if not user:
        # try to authenticate with username/password
        user = User.query.filter_by(username=username_or_token).first()
        if not user or not user.verify_password(password):
            return False
    g.user = user
    return True


@auth.error_handler
def unauthorized():
    return make_response(jsonify({'error': 'Unauthorized access'}, 401))


class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), index=True, unique=True)
    password_hash = db.Column(db.String(256))
    task = db.relationship('Task', backref='user', lazy='dynamic')

    def __init__(self, username=""):
        self.username = username

    def __repr__(self):
        return '<User username:{}, password_hash:{}>'.format(self.username, self.password_hash)

    def hash_password(self, password):
        self.password_hash = pwd_context.encrypt(password)

    def verify_password(self, password):
        return pwd_context.verify(password, self.password_hash)

    def generate_auth_token(self, expiration=600):
        s = Serializer(app.config['SECRET_KEY'], expires_in=expiration)
        return s.dumps({'id': self.id})

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except SignatureExpired:
            return None
        except BadSignature:
            return None
        user = User.query.get(data['id'])
        return user


class Task(db.Model):
    __tablename__ = 'task'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    description = db.Column(db.Text)
    done = db.Column(db.Boolean)
    #user = db.relationship('User', backref='task', lazy='dynamic')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


    def __init__(self, title="", description="", done="", user_id=""):
        self.title = title
        self.description = description
        self.done = done
        self.user_id = user_id

    def __repr__(self):
        return '<Task id:{}, title:{}, description:{}, done:{}>'.format(self.id, self.title, self.description, self.done)


def model2dict(model):
    if "_sa_instance_state" in model.__dict__.keys():
        model.__dict__.pop("_sa_instance_state")
    return model.__dict__


@app.route('/todo/api/v1/token')
@auth.login_required
def get_auth_token():
    token = g.user.generate_auth_token()
    return jsonify({'token': token.decode('ascii')})

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
    username = request.get_json()['username']
    password = request.get_json()['password']
    if not request.is_json:
        abort(400)  # request is not json
    if username is None or password is None:
        abort(400)  # missing arguments
    if User.query.filter_by(username=username).first() is not None:
        abort(400)  # existing user

    # レコード作成
    user = User(username=username)
    user.hash_password(password)
    db.session.add(user)
    db.session.commit()
    print(user)  # これがないとレスポンスボディのuser中身が表示されない

    return jsonify({'username': user.username}), 201, {'Location': url_for('get_user', user_id=user.id, _external=True)}


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
    if 'username' in request.get_json() and type(request.get_json()['username']) != str:
        abort(400)
    if 'password' in request.get_json() and type(request.get_json()['password']) != str:
        abort(400)

    # レコード更新
    if 'username' in request.get_json():
        user.username = request.get_json()['username']
    if 'password' in request.get_json():
        user.password = request.get_json()['password']
    db.session.commit()
    print(user)  # これがないとレスポンスボディのuser中身が表示されない

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
    #user = User.query.filter_by(username=auth.username()).first()  # For BasicAuth
    #tasks = [model2dict(task) for task in Task.query.filter_by(user_id=user.id)]  # For BasicAuth
    tasks = [model2dict(task) for task in Task.query.all()]
    return jsonify({'tasks': [make_public_task(task) for task in tasks]})

@app.route('/todo/api/v1/tasks/<int:task_id>', methods=['GET'])
@auth.login_required
def get_task(task_id):
    # レコード参照
    #user = User.query.filter_by(username=auth.username()).first()  # For BasicAuth
    #task = Task.query.filter_by(id=task_id, user_id=user.id).first()  # For BasicAuth
    task = Task.query.get(task_id)
    if not task:
        abort(404)
    return jsonify({'tasks': make_public_task(model2dict(task))})


@app.route('/todo/api/v1/tasks', methods=['POST'])
@auth.login_required
def create_task():
    # リクエストチェック -JSONかつtitle含む
    if not request.is_json:
        abort(400)
    if 'title' not in request.get_json():
        abort(400)
    if 'user_id' not in request.get_json():
        abort(400)

    # レコード参照
    #user = User.query.filter_by(username=auth.username()).first()  # For BasicAuth

    # descriptionがあれば代入
    if 'description' in request.get_json():
        description = request.get_json()['description']
    else:
        description = ''

    # レコード作成
    #task = Task(request.get_json()['title'], description, False, user.id)  # For BasicAuth
    task = Task(request.get_json()['title'], description, False, request.get_json()['user_id'])
    db.session.add(task)
    db.session.commit()

    print(task)  # これがないとレスポンスボディのtask中身が表示されない

    return jsonify({'task': make_public_task(model2dict(task))}), 201


@app.route('/todo/api/v1/tasks/<int:task_id>', methods=['PUT'])
@auth.login_required
def update_task(task_id):
    # リクエストチェック
    if not request.is_json:
        abort(400)

    # レコード参照
    #user = User.query.filter_by(username=auth.username()).first()  # For BasicAuth
    #task = Task.query.filter_by(id=task_id, user_id=user.id).first()  # For BasicAuth
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
    db.session.commit()

    print(task)  # これがないとレスポンスボディのtask中身が表示されない

    return jsonify({'task': make_public_task(model2dict(task))})


@app.route('/todo/api/v1/tasks/<int:task_id>', methods=['DELETE'])
@auth.login_required
def delete_task(task_id):
    # レコード参照
    #user = User.query.filter_by(username=auth.username()).first()  # For BasicAuth
    #task = Task.query.filter_by(id=task_id, user_id=user.id).first()  # For BasicAuth
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
