from flask import Flask, render_template, request, jsonify
from datetime import datetime

app = Flask(__name__)

# 模拟数据库（新增了时间戳字段）
mock_kucun = [
    {"id": 1, "food_name": "波士顿龙虾", "in_time": "2026-06-18", "exp_time": "2026-06-25", "status": "normal"},
    {"id": 2, "food_name": "冰鲜三文鱼", "in_time": "2026-06-10", "exp_time": "2026-06-15", "status": "expired"}
]
mock_queue = []


@app.route('/')
def index_page(): return render_template('index.html')


@app.route('/user')
def user_page(): return render_template('user.html')


@app.route('/login')
def login_page(): return render_template('login.html')


@app.route('/admin_menu')
def admin_menu_page(): return render_template('admin_menu.html')


@app.route('/queue_admin')
def queue_admin_page(): return render_template('queue_admin.html')


@app.route('/kucun')
def kucun_page(): return render_template('kucun.html')


@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json or {}
    if data.get('username') == 'admin' and data.get('password') == 'admin123':
        return jsonify({"code": 200, "msg": "登录成功"})
    return jsonify({"code": 401, "msg": "账号或密码错误"})


# ----------------- 库存时间管理拓展 API -----------------
@app.route('/api/kucun/list', methods=['GET'])
def api_kucun_list():
    today_str = datetime.now().strftime('%Y-%m-%d')
    # 动态根据当前时间更新安全/过期状态
    for item in mock_kucun:
        if item.get('exp_time') and item['exp_time'] < today_str:
            item['status'] = 'expired'
        else:
            item['status'] = 'normal'
    return jsonify({"code": 200, "data": mock_kucun})


@app.route('/api/kucun/add', methods=['POST'])
def api_kucun_add():
    data = request.json or {}
    name = data.get('food_name')
    in_time = data.get('in_time')
    exp_time = data.get('exp_time')

    if name:
        today_str = datetime.now().strftime('%Y-%m-%d')
        status = 'expired' if exp_time < today_str else 'normal'
        mock_kucun.append({
            "id": len(mock_kucun) + 1,
            "food_name": name,
            "in_time": in_time,
            "exp_time": exp_time,
            "status": status
        })
    return jsonify({"code": 200})


@app.route('/api/kucun/delete', methods=['POST'])
def api_kucun_delete():
    data = request.json or {}
    global mock_kucun
    mock_kucun = [i for i in mock_kucun if i['id'] != data.get('id')]
    return jsonify({"code": 200})


@app.route('/api/kucun/clear_expired', methods=['POST'])
def api_kucun_clear_expired():
    global mock_kucun
    today_str = datetime.now().strftime('%Y-%m-%d')
    mock_kucun = [i for i in mock_kucun if i['exp_time'] >= today_str]
    return jsonify({"code": 200})


# ----------------- 排队核心 API -----------------
@app.route('/api/queue/take', methods=['POST'])
def api_take_queue():
    data = request.json or {}
    q_type = data.get('type', 'normal')
    p_count = data.get('people_count', 1)
    prefix = 'V' if q_type == 'VIP' else 'N'
    new_number = f"{prefix}{len(mock_queue) + 1:03d}"
    ahead = len([i for i in mock_queue if i['status'] == 'waiting'])
    mock_queue.append(
        {"id": len(mock_queue) + 1, "queue_number": new_number, "queue_type": q_type, "people_count": p_count,
         "status": "waiting"})
    return jsonify({"code": 200, "data": {"queue_number": new_number, "ahead_count": ahead}})


@app.route('/api/queue/list', methods=['GET'])
def api_queue_list():
    waiting = [i for i in mock_queue if i['status'] == 'waiting']
    waiting.sort(key=lambda x: (0 if x['queue_type'] == 'VIP' else 1, x['id']))
    return jsonify({"code": 200, "data": waiting})


@app.route('/api/queue/operate', methods=['POST'])
def api_queue_operate():
    data = request.json or {}
    for item in mock_queue:
        if item['id'] == data.get('id'):
            if data.get('action') == 'call':
                item['status'] = 'called'
            elif data.get('action') == 'miss':
                item['status'] = 'missed'
    return jsonify({"code": 200})


if __name__ == '__main__':
    app.run(debug=True, port=5000)