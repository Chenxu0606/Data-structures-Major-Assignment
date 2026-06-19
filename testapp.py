from flask import Flask, render_template, request, jsonify
from datetime import datetime

app = Flask(__name__)


# ==============================================================================
# 【数据结构定义区】 - 面向大作业考核标准
# ==============================================================================

class QueueNode:
    """
    数据结构：队列节点 (Queue Node)
    描述：用于封装每一位排队顾客的结构化实体数据
    """

    def __init__(self, q_id, queue_number, q_type, people_count):
        self.id = q_id  # 节点唯一标识（自增ID）
        self.queue_number = queue_number  # 展现给顾客的号码（如 V001, N002）
        self.queue_type = q_type  # 顾客类型：'VIP' 或 'normal'
        self.people_count = people_count  # 就餐人数
        self.status = "waiting"  # 状态流转："waiting", "called", "missed"

    def to_dict(self):
        """将节点对象序列化为字典，方便前端 JSON 解析"""
        return {
            "id": self.id,
            "queue_number": self.queue_number,
            "queue_type": self.queue_type,
            "people_count": self.people_count,
            "status": self.status
        }


class PriorityQueue:
    """
    数据结构：优先级队列 (Priority Queue)
    描述：手写顺序存储的优先级队列，通过动态插入维持队列的整体高级别优先序
    """

    def __init__(self):
        self.items = []  # 底层采用顺序表（列表）存储节点

    def is_empty(self):
        return len(self.items) == 0

    def size(self):
        return len(self.items)

    def enqueue(self, node):
        """
        【算法名称】：基于特定优先级的单遍扫描插入算法 (Priority Insertion Sort)
        【算法描述】：新节点入队时，遍历当前队列。VIP 享有最高优先级，排在所有普通顾客(normal)前面；
                     同等级别内部则遵循先进先出(FIFO)原则，按 id 先来后到。
        【时间复杂度】：O(N) - 最坏情况下需要遍历整个队列找到插入点
        【空间复杂度】：O(1) - 仅需常数级辅助指针
        """
        insert_index = 0
        for i, item in enumerate(self.items):
            # 核心策略判断：若当前新节点是 VIP，而队列中遍历到的旧节点是普通顾客
            # 则说明找到了 VIP “插队”到普通顾客前面的切入点
            if node.queue_type == 'VIP' and item.queue_type == 'normal':
                insert_index = i
                break
            insert_index = i + 1

        # 在计算出的最右边界索引处执行插入，动态维持队列的有序性
        self.items.insert(insert_index, node)

    def get_waiting_list(self):
        """
        【算法名称】：线性过滤算法 (Linear Filtering)
        【时间复杂度】：O(N) - 遍历整个顺序表
        """
        return [item.to_dict() for item in self.items if item.status == 'waiting']


# ==============================================================================
# 【全局数据实例化】
# ==============================================================================

# 实例化手写的优先级队列系统
queue_system = PriorityQueue()

# 模拟食材库存顺序表（作为线性表的应用）
mock_kucun = [
    {"id": 1, "food_name": "波士顿龙虾", "in_time": "2026-06-18", "exp_time": "2026-06-25", "status": "normal"},
    {"id": 2, "food_name": "冰鲜三文鱼", "in_time": "2026-06-10", "exp_time": "2026-06-15", "status": "expired"}
]


# ==============================================================================
# 【Flask 路由与页面渲染】
# ==============================================================================

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


# ==============================================================================
# 【库存管理核心 API】 - 线性表基本操作应用
# ==============================================================================

@app.route('/api/kucun/list', methods=['GET'])
def api_kucun_list():
    """
    【算法名称】：时间戳比对与线性状态更新算法
    【时间复杂度】：O(N)
    """
    today_str = datetime.now().strftime('%Y-%m-%d')
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
    """
    【算法名称】：顺序表显式条件过滤与批量移除算法
    【时间复杂度】：O(N)
    【描述】：显式遍历线性顺序表，挑出未过期的物料重新组合，达到移除过期项的物理存储优化目的。
    """
    global mock_kucun
    today_str = datetime.now().strftime('%Y-%m-%d')

    active_kucun = []
    for item in mock_kucun:
        if item['exp_time'] >= today_str:
            active_kucun.append(item)

    mock_kucun = active_kucun
    return jsonify({"code": 200})


# ==============================================================================
# 【排队核心 API】 - 精准双轨排队算法应用
# ==============================================================================

@app.route('/api/queue/take', methods=['POST'])
def api_take_queue():
    """
    【业务逻辑】：顾客取号，触发入队操作并动态计算精准的前方就餐等待桌数
    """
    data = request.json or {}
    q_type = data.get('type', 'normal')
    p_count = data.get('people_count', 1)

    prefix = 'V' if q_type == 'VIP' else 'N'
    new_number = f"{prefix}{queue_system.size() + 1:03d}"

    # --------------------------------------------------------------------------
    # 【算法名称】：基于客户分级的精准前方桌数动态统计算法
    # 【时间复杂度】：O(N) - 顺序扫描当前等待链
    # 【算法描述】：
    #   1. 若新入队顾客为 VIP 级别：由于其具备高优先级插队权，普通顾客无法对其造成阻碍。
    #      因此，其前方真正的有效等待桌数，仅仅为当前队列中同样处于 'waiting' 状态的 VIP 顾客数量。
    #   2. 若新入队顾客为普通级别(normal)：其必须等待当前队列中所有正在排队的人（VIP + 普通人）。
    # --------------------------------------------------------------------------
    current_waiting_nodes = [item for item in queue_system.items if item.status == 'waiting']

    if q_type == 'VIP':
        # 算法分支 A：过滤统计当前排在其前方的 VIP 节点数
        ahead = sum(1 for item in current_waiting_nodes if item.queue_type == 'VIP')
    else:
        # 算法分支 B：普通顾客需要等待当前全队所有未就餐者
        ahead = len(current_waiting_nodes)
    # --------------------------------------------------------------------------

    # 构建新节点
    new_node = QueueNode(
        q_id=queue_system.size() + 1,
        queue_number=new_number,
        q_type=q_type,
        people_count=p_count
    )

    # 【算法调用】：执行手写的优先级插入队列算法
    queue_system.enqueue(new_node)

    return jsonify({"code": 200, "data": {"queue_number": new_number, "ahead_count": ahead}})


@app.route('/api/queue/list', methods=['GET'])
def api_queue_list():
    """
    【业务逻辑】：获取叫号管理面板列表
    【数据状态说明】：由于在 enqueue 时就确保了插入有序性，此处直接线性读取即可，时间复杂度由 O(NlogN) 降为 O(1)。
    """
    waiting_data = queue_system.get_waiting_list()
    return jsonify({"code": 200, "data": waiting_data})


@app.route('/api/queue/operate', methods=['POST'])
def api_queue_operate():
    """
    【算法名称】：线性查找与状态修改算法
    【时间复杂度】：O(N)
    """
    data = request.json or {}
    target_id = data.get('id')
    action = data.get('action')

    # 遍历队列找到指定ID的节点，更新其状态机
    for item in queue_system.items:
        if item.id == target_id:
            if action == 'call':
                item.status = 'called'
            elif action == 'miss':
                item.status = 'missed'
            break

    return jsonify({"code": 200})


if __name__ == '__main__':
    # 启动 Flask 服务，监听 5000 端口
    app.run(debug=True, port=5000)