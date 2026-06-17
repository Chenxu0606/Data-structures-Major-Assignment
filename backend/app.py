import time
from bson import ObjectId
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from pymongo import MongoClient, ASCENDING

app = Flask(__name__)
app.config['SECRET_KEY'] = 'zhice_ai_secret_key_2026'

# 允许跨域请求，满足 Vue 前后端分离开发
CORS(app, resources={r"/api/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*")

# ==========================================
# 💾 MongoDB 数据库初始化
# ==========================================
try:
    client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)
    db = client["zhice_restaurant_db"]
    # 测试连接
    client.server_info()
    print("⚡ [智策成功连接] MongoDB 数据库连接成功！")
except Exception as e:
    print(f"❌ [数据库连接失败] 请确保 MongoDB 已启动。错误信息: {e}")
    exit(1)

# 集合定义
coll_queue = db["queues"]  # 排队队列集合
coll_inventory = db["inventory"]  # 食材最小堆库存集合
coll_counters = db["counters"]  # 票号计数器
coll_tables = db["tables"]  # 物理桌位资产集合

# 初始化物理桌位与计数器（如果数据库是空的）
if coll_tables.count_documents({}) == 0:
    coll_tables.insert_one({"_id": "status", "S": 0, "M": 0, "L": 0})
if coll_counters.count_documents({}) == 0:
    coll_counters.insert_one(
        {"_id": "ticket_counters", "S": 1, "M": 1, "L": 1, "VIP": 1, "total_served": 0, "total_tickets": 0})


# ==========================================
# 🛠️ 核心辅助算法：状态广播与大屏同步
# ==========================================
def get_system_snapshot():
    """获取全店排队资产与大屏 KPI 的最新快照"""
    # 计数器
    counters = coll_counters.find_one({"_id": "ticket_counters"})
    # 当前各队列等待人数
    s_wait = coll_queue.count_documents({"queue_type": "S", "status": "waiting"})
    m_wait = coll_queue.count_documents({"queue_type": "M", "status": "waiting"})
    l_wait = coll_queue.count_documents({"queue_type": "L", "status": "waiting"})
    vip_wait = coll_queue.count_documents({"queue_type": "VIP", "status": "waiting"})

    # 桌位占用情况
    tables = coll_tables.find_one({"_id": "status"})

    return {
        "kpi": {
            "total_tickets": counters.get("total_tickets", 0),
            "total_served": counters.get("total_served", 0),
            "total_wait": s_wait + m_wait + l_wait + vip_wait
        },
        "queues": {
            "S_len": s_wait, "M_len": m_wait, "L_len": l_wait, "VIP_len": vip_wait
        },
        "tables": {
            "occupied_s": tables.get("S", 0), "occupied_m": tables.get("M", 0), "occupied_l": tables.get("L", 0),
            "total_s": 4, "total_m": 3, "total_l": 2
        }
    }


def broadcast_screen_update():
    """通过 WebSocket 全局大屏秒级同步数据"""
    snapshot = get_system_snapshot()
    socketio.emit("screen_sync", snapshot)


# ==========================================
# 📢 智能叫号与排队系统 API
# ==========================================
@app.route('/api/queue/snapshot', methods=['GET'])
def api_get_snapshot():
    return jsonify(get_system_snapshot())


@app.route('/api/queue/enqueue', methods=['POST'])
def api_enqueue():
    """顾客自主取号 API"""
    data = request.json or {}
    customer_name = data.get("customer_name", "").strip()
    party_size = data.get("party_size")
    is_vip = data.get("is_vip", False)

    if not customer_name or not isinstance(party_size, int) or party_size <= 0:
        return jsonify({"status": "error", "message": "参数非法，姓名和就餐人数必填！"}), 400

    # 确定桌型与票号前缀
    if is_vip:
        q_type = "VIP"
        prefix = "V"
        display_name = "VIP 专属特权"
    else:
        if party_size <= 2:
            q_type = "S"; prefix = "S"; display_name = "舒适小桌 (1-2人)"
        elif 3 <= party_size <= 4:
            q_type = "M"; prefix = "M"; display_name = "精致中桌 (3-4人)"
        else:
            q_type = "L"; prefix = "L"; display_name = "宽敞大桌 (5人以上)"

    # 检查当前是否有排队，如果没有排队，尝试直接智能调配桌位资产（绿色通道）
    current_wait = coll_queue.count_documents({"queue_type": q_type, "status": "waiting"})
    if current_wait == 0:
        tables = coll_tables.find_one({"_id": "status"})
        allocated = False
        alloc_msg = ""

        if party_size <= 2:
            if tables["S"] < 4:
                coll_tables.update_one({"_id": "status"},
                                       {"$inc": {"S": 1}}); allocated = True; alloc_msg = "分配成功：[标准小桌]"
            elif tables["M"] < 3:
                coll_tables.update_one({"_id": "status"},
                                       {"$inc": {"M": 1}}); allocated = True; alloc_msg = "小桌爆满，升级指派：[中桌]"
            elif tables["L"] < 2:
                coll_tables.update_one({"_id": "status"},
                                       {"$inc": {"L": 1}}); allocated = True; alloc_msg = "极度紧张，特殊放行：[大桌]"
        elif 3 <= party_size <= 4:
            if tables["M"] < 3:
                coll_tables.update_one({"_id": "status"},
                                       {"$inc": {"M": 1}}); allocated = True; alloc_msg = "分配成功：[标准中桌]"
            elif tables["L"] < 2:
                coll_tables.update_one({"_id": "status"},
                                       {"$inc": {"L": 1}}); allocated = True; alloc_msg = "中桌爆满，升级指派：[大桌]"
        else:
            if tables["L"] < 2: coll_tables.update_one({"_id": "status"},
                                                       {"$inc": {"L": 1}}); allocated = True; alloc_msg = "分配成功：[标准大桌]"

        if allocated:
            # 扣减成功，直接放行，更新全局总数
            coll_counters.update_one({"_id": "ticket_counters"}, {"$inc": {"total_tickets": 1, "total_served": 1}})
            broadcast_screen_update()
            return jsonify({
                "status": "green_channel",
                "message": f"欢迎您，{customer_name}！店内当前有空闲桌位，已为您开启免排队绿色通道直接就餐！",
                "alloc_msg": alloc_msg
            })

    # 必须进入常规排队流程
    counters = coll_counters.find_and_modify(
        query={"_id": "ticket_counters"},
        update={"$inc": {f"{q_type}": 1, "total_tickets": 1}},
        new=True
    )
    ticket_num = f"{prefix}{counters[q_type] - 1:03d}"

    # 写入排队表
    coll_queue.insert_one({
        "ticket_num": ticket_num,
        "customer_name": customer_name,
        "party_size": party_size,
        "queue_type": q_type,
        "status": "waiting",
        "timestamp": time.time()
    })

    broadcast_screen_update()
    return jsonify({
        "status": "queued",
        "ticket_num": ticket_num,
        "display_name": display_name,
        "message": "对应桌型已满，成功进入排队序列。"
    })


@app.route('/api/queue/call', methods=['POST'])
def api_call_customer():
    """商家叫号调度系统"""
    # 叫号优先级：VIP -> S -> M -> L
    next_customer = None
    for q_type in ["VIP", "S", "M", "L"]:
        next_customer = coll_queue.find_one({"queue_type": q_type, "status": "waiting"},
                                            sort=[("timestamp", ASCENDING)])
        if next_customer:
            break

    if not next_customer:
        return jsonify({"status": "empty", "message": "当前排队队列中没有正在等待的顾客。"})

    party_size = next_customer["party_size"]
    tables = coll_tables.find_one({"_id": "status"})
    allocated = False
    table_field = None

    # 动态匹配释放规则
    if party_size <= 2:
        if tables["S"] < 4:
            table_field = "S"
        elif tables["M"] < 3:
            table_field = "M"
        elif tables["L"] < 2:
            table_field = "L"
    elif 3 <= party_size <= 4:
        if tables["M"] < 3:
            table_field = "M"
        elif tables["L"] < 2:
            table_field = "L"
    else:
        if tables["L"] < 2: table_field = "L"

    if not table_field:
        return jsonify({"status": "full",
                        "message": f"呼叫失败！全店对应物理桌位已饱和，无法安置 {next_customer['ticket_num']} 号，请先释放餐桌资产。"}), 400

    # 改变状态，更新资产
    coll_queue.update_one({"_id": next_customer["_id"]}, {"$set": {"status": "served"}})
    coll_tables.update_one({"_id": "status"}, {"$inc": {table_field: 1}})
    coll_counters.update_one({"_id": "ticket_counters"}, {"$inc": {"total_served": 1}})

    broadcast_screen_update()

    # 顺便读取当前堆顶最危急的食材，为商家提供 AI 推销话术
    top_ing = coll_inventory.find_one({}, sort=[("expiry_days", ASCENDING)])
    ai_tip = "💡 智策看板：店内库存储备充沛健康。"
    if top_ing:
        if top_ing["expiry_days"] <= 0:
            ai_tip = f"❌ 智策预警：【{top_ing['name']}】已过期，请前往库存页面一键报废销毁！"
        elif top_ing["expiry_days"] <= 2:
            ai_tip = f"🔊 智策智能推介：食材【{top_ing['name']}】还有 {top_ing['expiry_days']} 天临期！建议本次带位时让服务员进行强力主推促销！"

    return jsonify({
        "status": "success",
        "ticket_num": next_customer["ticket_num"],
        "customer_name": next_customer["customer_name"],
        "ai_tip": ai_tip
    })


@app.route('/api/queue/release', methods=['POST'])
def api_release_table():
    """离座资产释放接口"""
    table_type = request.json.get("table_type")  # "S", "M", "L"
    tables = coll_tables.find_one({"_id": "status"})

    if not table_type or table_type not in ["S", "M", "L"]:
        return jsonify({"status": "error", "message": "桌位类型不合规"}), 400

    if tables.get(table_type, 0) <= 0:
        return jsonify({"status": "error", "message": "该类型桌位当前未被占用，无需释放！"}), 400

    coll_tables.update_one({"_id": "status"}, {"$inc": {table_type: -1}})
    broadcast_screen_update()
    return jsonify({"status": "success", "message": f"成功空出 1 张 [{table_type}] 型餐桌！"})


# ==========================================
# 🍎 智策临期食材堆（Inventory CRUD + 级联消库）
# ==========================================
@app.route('/api/inventory/list', methods=['GET'])
def api_get_inventory():
    """获取通过临期天数升序排列的食材列表（映射底层最小堆逻辑）"""
    items = list(coll_inventory.find({}, sort=[("expiry_days", ASCENDING)]))
    for item in items:
        item["_id"] = str(item["_id"])
    return jsonify({"inventory": items})


@app.route('/api/inventory/add', methods=['POST'])
def api_add_inventory():
    data = request.json or {}
    name = data.get("name", "").strip()
    qty = data.get("qty")
    unit = data.get("unit", "").strip()
    expiry_days = data.get("expiry_days")

    if not name or not unit or not isinstance(qty, int) or not isinstance(expiry_days, int) or qty <= 0:
        return jsonify({"status": "error", "message": "输入格式有误，数量及保质期天数必须是正整数！"}), 400

    coll_inventory.insert_one({
        "name": name, "qty": qty, "unit": unit, "expiry_days": expiry_days
    })
    return jsonify({"status": "success", "message": f"食材【{name}】成功录入数据堆储备。"})


@app.route('/api/inventory/update', methods=['PUT'])
def api_update_inventory():
    """修改单条食材的基础信息"""
    data = request.json or {}
    item_id = data.get("id")
    name = data.get("name")
    qty = data.get("qty")
    unit = data.get("unit")
    expiry_days = data.get("expiry_days")

    if not item_id: return jsonify({"status": "error", "message": "缺少食材 ID"}), 400

    update_fields = {}
    if name: update_fields["name"] = name
    if isinstance(qty, int) and qty > 0: update_fields["qty"] = qty
    if unit: update_fields["unit"] = unit
    if isinstance(expiry_days, int): update_fields["expiry_days"] = expiry_days

    result = coll_inventory.update_one({"_id": ObjectId(item_id)}, {"$set": update_fields})
    if result.matched_count:
        return jsonify({"status": "success", "message": "修改成功！"})
    return jsonify({"status": "error", "message": "未找到指定食材"}), 404


@app.route('/api/inventory/delete/<item_id>', methods=['DELETE'])
def api_delete_inventory(item_id):
    """直接删除某条特定数据（如手工清理、人工修正）"""
    result = coll_inventory.delete_one({"_id": ObjectId(item_id)})
    if result.deleted_count:
        return jsonify({"status": "success", "message": "指定批次已被成功移除。"})
    return jsonify({"status": "error", "message": "删除失败，物品不存在。"}), 404


@app.route('/api/inventory/consume', methods=['POST'])
def api_consume_cascade():
    """【级联消库核心算法】管理员自主控量一键扣除"""
    data = request.json or {}
    req_qty = data.get("qty")

    if not isinstance(req_qty, int) or req_qty <= 0:
        return jsonify({"status": "error", "message": "消耗数量必须为正整数！"}), 400

    # 1. 查找目前堆顶最紧急的批次
    top_batch = coll_inventory.find_one({}, sort=[("expiry_days", ASCENDING)])
    if not top_batch:
        return jsonify({"status": "empty", "message": "当前库存中空空如也，无任何物料可扣减。"})

    # 2. 安全检查：如果堆顶第一批已经过期，强行阻断进行安全报废，不许扣减正常消耗
    if top_batch["expiry_days"] <= 0:
        coll_inventory.delete_one({"_id": top_batch["_id"]})
        return jsonify({
            "status": "expired_blocked",
            "message": f"🚨 智能防灾机制强行阻断！当前最紧急批次【{top_batch['name']}】已过期 {abs(top_batch['expiry_days'])} 天！系统已拒绝本次扣除请求，并自动对该批次总计 {top_batch['qty']} {top_batch['unit']} 执行【整批安全出堆报废销毁】流程！"
        })

    # 3. 级联滚动消库计算
    remaining_to_deduct = req_qty
    consumed_flow = []

    # 按到期紧急度从小到大依次遍历
    all_active_batches = list(coll_inventory.find({}, sort=[("expiry_days", ASCENDING)]))

    for batch in all_active_batches:
        if remaining_to_deduct <= 0:
            break

        # 途中如果碰到过期的，则不扣除此批次，直接终止向下传播
        if batch["expiry_days"] <= 0:
            continue

        b_id = batch["_id"]
        b_name = batch["name"]
        b_qty = batch["qty"]
        b_unit = batch["unit"]

        if b_qty > remaining_to_deduct:
            # 当前批次足够扣减
            coll_inventory.update_one({"_id": b_id}, {"$inc": {"qty": -remaining_to_deduct}})
            consumed_flow.append({"name": b_name, "qty": remaining_to_deduct, "unit": b_unit})
            remaining_to_deduct = 0
        else:
            # 当前批次不够扣，需要全额吃掉它，然后寻找下一批
            coll_inventory.delete_one({"_id": b_id})
            consumed_flow.append({"name": b_name, "qty": b_qty, "unit": b_unit})
            remaining_to_deduct -= b_qty

    if remaining_to_deduct == 0:
        return jsonify({
            "status": "success",
            "message": f"🎉 成功扣除管理员指定的 {req_qty} 个资产单位！",
            "flow": consumed_flow
        })
    else:
        total_done = req_qty - remaining_to_deduct
        return jsonify({
            "status": "partial",
            "message": f"⚠️ 全可用库存告罄！向系统请求了 {req_qty} 个单位，但目前全库可用活货仅剩余 {total_done} 个单位。",
            "shortage": remaining_to_deduct,
            "flow": consumed_flow
        })


@app.route('/api/inventory/time_pass', methods=['POST'])
def api_time_travel():
    """时间推移：全库食材保质期天数减1天"""
    coll_inventory.update_many({}, {"$inc": {"expiry_days": -1}})
    return jsonify({"status": "success", "message": "⏳ 时空矩阵推移 1 天！全库食材生命周期缩减，已触发最小堆序列重整。"})

@app.route("/")
def home():
    return render_template("index.html")
# ==========================================
# 🚀 启动 Flask 服务
# ==========================================
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)