from flask import Flask, render_template, request, jsonify
import datetime

app = Flask(__name__)


# ==============================================================================
# 核心数据结构与模拟数据库初始化
# ==============================================================================

class QueueNode:
    def __init__(self, node_id, queue_number, table_category, people_count, queue_type):
        self.id = int(node_id)
        self.queue_number = queue_number
        self.table_category = table_category  # A-小桌, B-中桌, C-大桌
        self.people_count = people_count
        self.queue_type = queue_type
        self.status = "waiting"  # waiting-等待中, called-已叫号, missed-已过号
        self.next = None


queue_head = None
node_counter = 4

# 初始化内置模拟数据
node1 = QueueNode(1, "A001", "A", 2, "普通用户")
node2 = QueueNode(2, "B002", "B", 4, "普通用户")
node3 = QueueNode(3, "C003", "C", 6, "普通用户")

queue_head = node1
node1.next = node2
node2.next = node3

customer_hash_table = {
    "A001": node1,
    "B002": node2,
    "C003": node3
}

# 食材仓储模拟数据
inventory_db = [
    {"id": 1, "food_name": "三文鱼", "in_time": "2026-06-12", "exp_time": "2026-06-15", "status": "expired"},
    {"id": 2, "food_name": "和牛肉", "in_time": "2026-06-16", "exp_time": "2026-06-25", "status": "safe"},
    {"id": 3, "food_name": "生菜", "in_time": "2026-06-18", "exp_time": "2026-06-21", "status": "safe"},
    {"id": 4, "food_name": "石斑鱼", "in_time": "2026-06-14", "exp_time": "2026-06-16", "status": "expired"},
    {"id": 5, "food_name": "五花肉", "in_time": "2026-06-15", "exp_time": "2026-06-19", "status": "expired"},
    {"id": 6, "food_name": "清远鸡", "in_time": "2026-06-17", "exp_time": "2026-06-22", "status": "safe"},
    {"id": 7, "food_name": "照烧酱", "in_time": "2026-05-01", "exp_time": "2026-07-01", "status": "safe"},
    {"id": 8, "food_name": "松露油", "in_time": "2026-04-10", "exp_time": "2026-06-10", "status": "expired"},
    {"id": 9, "food_name": "鸡蛋", "in_time": "2026-06-10", "exp_time": "2026-06-24", "status": "safe"},
    {"id": 10, "food_name": "虾仁", "in_time": "2026-06-16", "exp_time": "2026-06-20", "status": "safe"}
]
kucun_counter = 11


# ==============================================================================
# 算法核心辅助函数
# ==============================================================================

def add_to_queue_linked_list(node):
    global queue_head
    customer_hash_table[node.queue_number] = node
    if not queue_head:
        queue_head = node
        return
    curr = queue_head
    while curr.next:
        curr = curr.next
    curr.next = node


def get_queue_list_by_status(status_filter=None):
    res = []
    curr = queue_head
    while curr:
        if status_filter is None or curr.status == status_filter:
            res.append({
                "id": curr.id,
                "queue_number": curr.queue_number,
                "table_category": curr.table_category,
                "people_count": curr.people_count,
                "queue_type": curr.queue_type,
                "status": curr.status
            })
        curr = curr.next
    return res


def count_ahead_and_time(table_category):
    """根据桌型算法计算前方同桌型等待桌数与动态预测时间"""
    ahead_count = 0
    curr = queue_head
    while curr:
        if curr.status == "waiting" and curr.table_category == table_category:
            ahead_count += 1
        curr = curr.next
    return ahead_count, ahead_count * 8


def update_inventory_status():
    """自动化动态校验食材是否超过保质期红线"""
    today_str = datetime.date.today().isoformat()
    for item in inventory_db:
        if item["exp_time"] < today_str:
            item["status"] = "expired"
        else:
            item["status"] = "safe"


# ==============================================================================
# 补齐所有前端页面的页面路由（防止跳转 404）
# ==============================================================================

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/user')
def user_portal():
    return render_template('user.html')


@app.route('/login')
def login_page():
    return render_template('login.html')


@app.route('/admin')
def admin_dashboard():
    return render_template('admin.html')


@app.route('/queue_admin')
def queue_management():
    return render_template('queue_admin.html')


@app.route('/kucun')
def kucun_management():
    return render_template('kucun.html')


# ==============================================================================
# 异步 API 核心控制接口
# ==============================================================================

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    if data.get('username') == "admin" and data.get('password') == "admin123":
        return jsonify({"code": 200, "msg": "认证成功"})
    return jsonify({"code": 403, "msg": "身份验证失败"})


@app.route('/api/queue/take', methods=['POST'])
def api_queue_take():
    global node_counter
    data = request.get_json() or {}
    try:
        people_count = int(data.get('people_count', 1))
    except ValueError:
        people_count = 1

    if people_count <= 2:
        category = "A"
    elif people_count <= 4:
        category = "B"
    else:
        category = "C"

    ahead_count, predict_time = count_ahead_and_time(category)
    queue_number = f"{category}{node_counter:03d}"

    new_node = QueueNode(node_counter, queue_number, category, people_count, "普通用户")
    add_to_queue_linked_list(new_node)
    node_counter += 1

    return jsonify({
        "code": 200,
        "data": {"queue_number": queue_number, "table_category": f"{category}桌型", "ahead_count": ahead_count,
                 "predict_time": predict_time}
    })


@app.route('/api/queue/list', methods=['GET'])
def api_queue_list():
    return jsonify(
        {"code": 200, "data": get_queue_list_by_status("waiting"), "called": get_queue_list_by_status("called")})


@app.route('/api/queue/all_status_for_screen', methods=['GET'])
def api_all_status():
    return jsonify({"code": 200, "data": get_queue_list_by_status(None)})


@app.route('/api/queue/operate', methods=['POST'])
def api_queue_operate():
    global queue_head
    data = request.get_json() or {}
    try:
        node_id = int(data.get('id'))
    except (ValueError, TypeError):
        return jsonify({"code": 400, "msg": "无效的节点ID"})
    action = data.get('action')

    # 1. 呼叫与过号
    if action in ['call', 'miss']:
        curr = queue_head
        while curr:
            if curr.id == node_id:
                if action == 'call':
                    curr.status = "called"
                elif action == 'miss':
                    curr.status = "missed"
                break
            curr = curr.next
        return jsonify({"code": 200, "msg": "调度指令执行成功"})

    # 2. 动态遍历重组插队（置顶）
    if action == 'jump':
        target_node = None
        if queue_head and queue_head.id == node_id:
            target_node = queue_head
            queue_head = queue_head.next
        else:
            prev = queue_head
            while prev and prev.next:
                if prev.next.id == node_id:
                    target_node = prev.next
                    prev.next = prev.next.next
                    break
                prev = prev.next

        if not target_node:
            return jsonify({"code": 404, "msg": "未找到活跃顾客"})

        orig_num = target_node.queue_number
        if not orig_num.startswith('S'):
            target_node.queue_number = f"S{orig_num[1:]}"
        target_node.queue_type = "现场紧急插队通道"
        target_node.status = "waiting"
        target_node.next = None

        customer_hash_table[target_node.queue_number] = target_node

        if not queue_head or (queue_head.status == "waiting" and not queue_head.queue_number.startswith('S')):
            target_node.next = queue_head
            queue_head = target_node
            return jsonify({"code": 200, "msg": "插队成功"})

        curr = queue_head
        while curr.next and curr.next.status == "waiting" and curr.next.queue_number.startswith('S'):
            curr = curr.next
        target_node.next = curr.next
        curr.next = target_node
        return jsonify({"code": 200, "msg": "插队成功"})

    # 3. 过号归队算法（重新排入等待队列第 3 位）
    if action == 'recover':
        target_node = None
        if queue_head and queue_head.id == node_id:
            target_node = queue_head
            queue_head = queue_head.next
        else:
            prev = queue_head
            while prev and prev.next:
                if prev.next.id == node_id:
                    target_node = prev.next
                    prev.next = prev.next.next
                    break
                prev = prev.next

        if not target_node:
            return jsonify({"code": 404, "msg": "未找到对应的过号记录"})

        target_node.status = "waiting"
        target_node.next = None

        if not queue_head:
            queue_head = target_node
            return jsonify({"code": 200, "msg": "恢复成功，已安排回队头"})

        curr = queue_head
        waiting_count = 0

        if curr.status == "waiting":
            waiting_count += 1

        while curr.next and waiting_count < 2:
            if curr.next.status == "waiting":
                waiting_count += 1
            if waiting_count == 2:
                break
            curr = curr.next

        target_node.next = curr.next
        curr.next = target_node

        return jsonify({"code": 200, "msg": "过号恢复成功，已自动插回等待队列第3位"})

    return jsonify({"code": 400, "msg": "无法识别的管理指令"})


# ==============================================================================
# 补齐后厨食材仓储模块对应的 API 核心控制接口（防止 kucun 页面请求 404）
# ==============================================================================

@app.route('/api/kucun/list', methods=['GET'])
def api_kucun_list():
    update_inventory_status()
    return jsonify({"code": 200, "data": inventory_db})


@app.route('/api/kucun/add', methods=['POST'])
def api_kucun_add():
    global kucun_counter
    data = request.get_json() or {}
    new_item = {
        "id": kucun_counter,
        "food_name": data.get('food_name'),
        "in_time": data.get('in_time'),
        "exp_time": data.get('exp_time'),
        "status": "safe"
    }
    inventory_db.append(new_item)
    kucun_counter += 1
    return jsonify({"code": 200, "msg": "登记入库成功"})


@app.route('/api/kucun/delete', methods=['POST'])
def api_kucun_delete():
    data = request.get_json() or {}
    global inventory_db
    inventory_db = [item for item in inventory_db if item["id"] != data.get('id')]
    return jsonify({"code": 200, "msg": "安全销毁成功"})


@app.route('/api/kucun/sort', methods=['POST'])
def api_kucun_sort():
    """按食材到期时间升序（经典冒泡排序算法）"""
    update_inventory_status()
    n = len(inventory_db)
    for i in range(n - 1):
        for j in range(0, n - i - 1):
            if inventory_db[j]["exp_time"] > inventory_db[j + 1]["exp_time"]:
                inventory_db[j], inventory_db[j + 1] = inventory_db[j + 1], inventory_db[j]
    return jsonify({"code": 200, "data": inventory_db})


@app.route('/api/kucun/clear_expired', methods=['POST'])
def api_kucun_clear_expired():
    global inventory_db
    update_inventory_status()
    inventory_db = [item for item in inventory_db if item["status"] != "expired"]
    return jsonify({"code": 200, "msg": "一键清除过期食品成功"})


if __name__ == '__main__':
    app.run(debug=True, port=5000)