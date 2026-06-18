from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# --------------------------------------------------------
# 模拟数据库（保证代码可直接运行，不影响你原有的真实数据库替换）
# --------------------------------------------------------
mock_queue = []
mock_kucun = [
    {"id": 1, "food_name": "波士顿龙虾", "status": "normal"},
    {"id": 2, "food_name": "冰鲜三文鱼", "status": "expired"}
]


# --------------------------------------------------------
# 基础页面渲染路由
# --------------------------------------------------------
@app.route('/')
def index_page():
    return render_template('index.html')


@app.route('/user')
def user_page():
    return render_template('user.html')


@app.route('/login')
def login_page():
    return render_template('login.html')


@app.route('/admin_menu')
def admin_menu_page():
    return render_template('admin_menu.html')


@app.route('/queue_admin')
def queue_admin_page():
    return render_template('queue_admin.html')


@app.route('/kucun_admin')
def kucun_admin_page():
    return render_template('kucun_admin.html')


# --------------------------------------------------------
# 核心业务安全 API
# --------------------------------------------------------
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json or {}
    username = data.get('username')
    password = data.get('password')
    if username == 'admin' and password == 'admin123':
        return jsonify({"code": 200, "msg": "登录成功"})
    return jsonify({"code": 401, "msg": "账号或密码错误"})


@app.route('/api/queue/take', methods=['POST'])
def api_take_queue():
    data = request.json or {}
    q_type = data.get('type', 'normal')
    p_count = data.get('people_count', 1)

    prefix = 'V' if q_type == 'VIP' else 'N'
    new_number = f"{prefix}{len(mock_queue) + 1:03d}"
    ahead = len([i for i in mock_queue if i['status'] == 'waiting'])

    mock_queue.append({
        "id": len(mock_queue) + 1,
        "queue_number": new_number,
        "queue_type": q_type,
        "people_count": p_count,
        "status": "waiting"
    })
    return jsonify({
        "code": 200,
        "data": {"queue_number": new_number, "ahead_count": ahead}
    })


@app.route('/api/queue/list', methods=['GET'])
def api_queue_list():
    waiting_list = [i for i in mock_queue if i['status'] == 'waiting']
    waiting_list.sort(key=lambda x: (0 if x['queue_type'] == 'VIP' else 1, x['id']))
    return jsonify({"code": 200, "data": waiting_list})


@app.route('/api/queue/operate', methods=['POST'])
def api_queue_operate():
    data = request.json or {}
    qid = data.get('id')
    action = data.get('action')
    for item in mock_queue:
        if item['id'] == qid:
            if action == 'call':
                item['status'] = 'called'
            elif action == 'miss':
                item['status'] = 'missed'
    return jsonify({"code": 200})


@app.route('/api/kucun/list', methods=['GET'])
def api_kucun_list():
    return jsonify({"code": 200, "data": mock_kucun})


@app.route('/api/kucun/add', methods=['POST'])
def api_kucun_add():
    data = request.json or {}
    name = data.get('food_name')
    if name:
        mock_kucun.append({"id": len(mock_kucun) + 1, "food_name": name, "status": "normal"})
    return jsonify({"code": 200})


@app.route('/api/kucun/delete', methods=['POST'])
def api_kucun_delete():
    data = request.json or {}
    kid = data.get('id')
    global mock_kucun
    mock_kucun = [i for i in mock_kucun if i['id'] != kid]
    return jsonify({"code": 200})


@app.route('/api/kucun/clear_expired', methods=['POST'])
def api_kucun_clear_expired():
    global mock_kucun
    mock_kucun = [i for i in mock_kucun if i['status'] != 'expired']
    return jsonify({"code": 200})


if __name__ == '__main__':
    app.run(debug=True, port=5000)