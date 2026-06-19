from flask import Flask, render_template, request, jsonify, redirect, url_for
import datetime

app = Flask(__name__)


# ==============================================================================
# 核心数据结构与模拟数据库初始化
# ==============================================================================

class QueueNode:
    def __init__(self, node_id, queue_number, table_category, people_count, queue_type):
        self.id = int(node_id)
        self.queue_number = queue_number  # 凭证号 如 A001, B001, S001
        self.table_category = table_category  # 桌型: A-小桌, B-中桌, C-大桌
        self.people_count = people_count  # 用餐人数
        self.queue_type = queue_type  # 通道描述
        self.status = "waiting"  # waiting-等待中, called-已叫号, missed-已过号
        self.next = None


node_counter = 4
queue_head = None

# 初始化一点模拟数据，方便你直接测试插队效果
node1 = QueueNode(1, "A001", "A", 2, "普通用户")
node2 = QueueNode(2, "V002", "B", 3, "VIP通道")
node3 = QueueNode(3, "B003", "B", 4, "普通用户")

# 组装初始双向/单向链表
queue_head = node1
node1.next = node2
node2.next = node3

# 全局哈希表，用于 O(1) 检索
customer_hash_table = {
    "A001": node1,
    "V002": node2,
    "B003": node3
}

# 后厨物料数据库
inventory_db = [
    {"id": 101, "food_name": "冰鲜三文鱼排", "in_time": "2026-06-15", "exp_time": "2026-06-18", "status": "expired"},
    {"id": 102, "food_name": "澳洲谷饲和牛肉", "in_time": "2026-06-16", "exp_time": "2026-06-22", "status": "safe"},
    {"id": 103, "food_name": "有机高山生菜", "in_time": "2026-06-18", "exp_time": "2026-06-20", "status": "safe"}
]
kucun_counter = 104


# ==============================================================================
# 辅助核心算法逻辑
# ==============================================================================

def add_to_queue_linked_list(node):
    """新顾客排队常规插入"""
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
    """遍历链表序列化输出"""
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
    ahead_count = 0
    curr = queue_head
    while curr:
        if curr.status == "waiting" and curr.table_category == table_category:
            ahead_count += 1
        curr = curr.next
    return ahead_count, ahead_count * 8


def update_inventory_status():
    today_str = datetime.date.today().isoformat()
    for item in inventory_db:
        if item["exp_time"] < today_str:
            item["status"] = "expired"
        else:
            item["status"] = "safe"


# ==============================================================================
# 页面核心路由
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
# API 异步控制核心接口
# ==============================================================================

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    if data.get('username') == "admin" and data.get('password') == "123456":
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

    new_node = QueueNode(node_counter, queue_number, category, people_count, "普通堂食通道")
    add_to_queue_linked_list(new_node)
    node_counter += 1

    return jsonify({
        "code": 200,
        "data": {
            "queue_number": queue_number,
            "table_category": f"{category}轨",
            "ahead_count": ahead_count,
            "predict_time": predict_time
        }
    })


@app.route('/api/queue/list', methods=['GET'])
def api_queue_list():
    waiting_nodes = get_queue_list_by_status("waiting")
    called_nodes = get_queue_list_by_status("called")
    return jsonify({"code": 200, "data": waiting_nodes, "called": called_nodes})


@app.route('/api/queue/all_status_for_screen', methods=['GET'])
def api_all_status():
    all_nodes = get_queue_list_by_status(status_filter=None)
    return jsonify({"code": 200, "data": all_nodes})


@app.route('/api/queue/search', methods=['GET'])
def api_queue_search():
    q_num = request.args.get('queue_number', '').strip()
    node = customer_hash_table.get(q_num)
    if node:
        return jsonify({
            "code": 200,
            "data": {"queue_number": node.queue_number, "status": node.status, "people_count": node.people_count,
                     "table_category": node.table_category}
        })
    return jsonify({"code": 404, "msg": "未找到记录"})


# ------------------------------------------------------------------------------
# 核心修复：操作控制台（支持一键动态插队指针调整）
# ------------------------------------------------------------------------------
@app.route('/api/queue/operate', methods=['POST'])
def api_queue_operate():
    global queue_head
    data = request.get_json() or {}

    # 强制将前端传来的 id 转为 int 避免类型匹配不上
    try:
        node_id = int(data.get('id'))
    except (ValueError, TypeError):
        return jsonify({"code": 400, "msg": "无效的节点ID"})

    action = data.get('action')

    # 处理呼叫和过号
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
        return jsonify({"code": 200, "msg": "调度成功"})

    # 处理插队逻辑
    if action == 'jump':
        target_node = None

        # 1. 从原链表中寻找到目标节点并将其完整剥离断开
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
            return jsonify({"code": 404, "msg": "未在队列中检索到该活跃顾客"})

        # 2. 修改特征属性：编号强制改写为 S 开头（同步触发大屏红色闪烁动画）
        orig_num = target_node.queue_number
        if not orig_num.startswith('S'):
            target_node.queue_number = f"S{orig_num[1:]}"
        target_node.queue_type = "插队用户"
        target_node.next = None

        # 更新哈希表映射关系
        customer_hash_table[target_node.queue_number] = target_node

        # 3. 寻找新卡位插入（排在所有已有插队节点的后面，普通和VIP的前面）
        if not queue_head:
            queue_head = target_node
            return jsonify({"code": 200, "msg": "插队成功"})

        if queue_head.status == "waiting" and not queue_head.queue_number.startswith('S'):
            target_node.next = queue_head
            queue_head = target_node
            return jsonify({"code": 200, "msg": "插队成功"})

        curr = queue_head
        while curr.next and curr.next.status == "waiting" and curr.next.queue_number.startswith('S'):
            curr = curr.next

        target_node.next = curr.next
        curr.next = target_node

        return jsonify({"code": 200, "msg": "插队成功"})


# ------------------------------------------------------------------------------
# 后厨仓储接口
# ------------------------------------------------------------------------------
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
    return jsonify({"code": 200, "msg": "成功"})


@app.route('/api/kucun/delete', methods=['POST'])
def api_kucun_delete():
    data = request.get_json() or {}
    global inventory_db
    inventory_db = [item for item in inventory_db if item["id"] != data.get('id')]
    return jsonify({"code": 200, "msg": "成功"})


@app.route('/api/kucun/sort', methods=['POST'])
def api_kucun_sort():
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
    return jsonify({"code": 200, "msg": "成功"})


if __name__ == '__main__':
    app.run(debug=True, port=5000)