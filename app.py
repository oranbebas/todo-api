"""
Additional todo
- Use database.
- For multiple users, add resource "users".
- Custmize GET request for "tasks", for example pagination, filtering by URL.
"""

from flask import Flask, jsonify, abort, make_response, request, url_for
from flask_httpauth import HTTPBasicAuth
auth = HTTPBasicAuth()


app = Flask(__name__)


@auth.get_password
def get_password(username):
    if username == 'miguel':
        return 'python'
    return None


@auth.error_handler
def unauthorized():
    return make_response(jsonify({'error': 'Unauthorized access'}, 401))


tasks = [
    {
        'id': 1,
        'title': 'Buy groceries',
        'description': 'Milk, Cheese, Pizza, Fruit, Tylenol',
        'done': False
    },
    {
        'id': 2,
        'title': 'Learn Python',
        'description': 'Neet to find a good Python tutorial on the web',
        'done': False
        }
]


@app.route('/todo/api/v1/tasks', methods=['GET'])
@auth.login_required
def get_tasks():
    return jsonify({'tasks': [make_public_task(task) for task in tasks]})


@app.route('/todo/api/v1/tasks/<int:task_id>', methods=['GET'])
@auth.login_required
def get_task(task_id):
    # リクエストチェック
    task = [task for task in tasks if task['id'] == task_id]
    if len(task) == 0:
        abort(404)

    return jsonify({'tasks': make_public_task(task[0])})


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

    task = {
        'id': tasks[-1]['id'] + 1,
        'title': request.get_json()['title'],
        'description': description,
        'done': False
    }
    tasks.append(task)

    return jsonify({'task': make_public_task(task)}), 201


@app.route('/todo/api/v1/tasks/<int:task_id>', methods=['PUT'])
@auth.login_required
def update_task(task_id):
    # リクエストチェック
    if not request.is_json:
        abort(400)
    task = [task for task in tasks if task['id'] == task_id]
    if len(task) == 0:
        abort(404)

    # 送信項目ごとの形式チェック
    if 'title' in request.get_json() and type(request.get_json()['title']) != str:
        abort(400)
    if 'description' in request.get_json() and type(request.get_json()['description']) != str:
        abort(400)
    if 'done' in request.get_json() and type(request.get_json()['done']) != bool:
        abort(400)

    # 送信項目ごとの更新
    if 'title' in request.get_json():
        task[0]['title'] = request.get_json()['title']
    if 'description' in request.get_json():
        task[0]['description'] = request.get_json()['description']
    if 'done' in request.get_json():
        task[0]['done'] = request.get_json()['done']

    return jsonify({'task': make_public_task(task[0])})


@app.route('/todo/api/v1/tasks/<int:task_id>', methods=['DELETE'])
@auth.login_required
def delete_task(task_id):
    # リクエストチェック
    task = [task for task in tasks if task['id'] == task_id]
    if len(task) == 0:
        abort(404)

    tasks.remove(task[0])

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
