import time
import mysql.connector
from mysql.connector import Error
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'zhice_ai_secret_key_2026'

# 允许跨域请求，满足 Vue 前后端分离开发
CORS(app, resources={r"/api/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*")

# ==========================================
# 💾 MySQL 8.4 数据库初始化
# ==========================================
def get_db_connection():
    """获取MySQL数据库连接"""
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='zhice_restaurant_db',
            user='root',
            password='123456',
            charset='utf8mb4'
        )
        return connection
    except Error as e:
        print(f"❌ [数据库连接失败] 请确保 MySQL 8.4 已启动。错误信息: {e}")
        return None

# 初始化数据库和表
def init_database():
    """初始化数据库和表结构"""
    try:
        # 先连接到MySQL服务器（不指定数据库）
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='root',
            charset='utf8mb4'
        )
        cursor = connection.cursor()
        
        # 创建数据库（如果不存在）
        cursor.execute("CREATE DATABASE IF NOT EXISTS zhice_restaurant_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.execute("USE zhice_restaurant_db")
        
        # 创建 queues 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS queues (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ticket_num VARCHAR(10) NOT NULL,
                customer_name VARCHAR(100) NOT NULL,
                party_size INT NOT NULL,
                queue_type VARCHAR(10) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'waiting',
                timestamp DOUBLE NOT NULL,
                INDEX idx_queue_status (queue_type, status),
                INDEX idx_timestamp (timestamp)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        
        # 创建 inventory 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                qty INT NOT NULL,
                unit VARCHAR(20) NOT NULL,
                expiry_days INT NOT NULL,
                INDEX idx_expiry (expiry_days)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        
        # 创建 counters 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS counters (
                id VARCHAR(50) PRIMARY KEY,
                S INT NOT NULL DEFAULT 1,
                M INT NOT NULL DEFAULT 1,
                L INT NOT NULL DEFAULT 1,
                VIP INT NOT NULL DEFAULT 1,
                total_served INT NOT NULL DEFAULT 0,
                total_tickets INT NOT NULL DEFAULT 0
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        
        # 创建 tables_status 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tables_status (
                id VARCHAR(50) PRIMARY KEY,
                S INT NOT NULL DEFAULT 0,
                M INT NOT NULL DEFAULT 0,
                L INT NOT NULL DEFAULT 0
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        
        # 初始化 counters 数据
        cursor.execute("SELECT COUNT(*) FROM counters WHERE id = 'ticket_counters'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO counters (id, S, M, L, VIP, total_served, total_tickets)
                VALUES ('ticket_counters', 1, 1, 1, 1, 0, 0)
            """)
        
        # 初始化 tables_status 数据
        cursor.execute("SELECT COUNT(*) FROM tables_status WHERE id = 'status'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO tables_status (id, S, M, L)
                VALUES ('status', 0, 0, 0)
            """)
        
        connection.commit()
        cursor.close()
        connection.close()
        print("⚡ [智策成功连接] MySQL 8.4 数据库初始化成功！")
        return True
    except Error as e:
        print(f"❌ [数据库初始化失败] 错误信息: {e}")
        return False

# 执行初始化
if not init_database():
    exit(1)


# ==========================================
# 🛠️ 核心辅助算法：状态广播与大屏同步
# ==========================================
def get_system_snapshot():
    """获取全店排队资产与大屏 KPI 的最新快照"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 计数器
    cursor.execute("SELECT * FROM counters WHERE id = 'ticket_counters'")
    counters = cursor.fetchone()
    
    # 当前各队列等待人数
    cursor.execute("SELECT COUNT(*) as cnt FROM queues WHERE queue_type = 'S' AND status = 'waiting'")
    s_wait = cursor.fetchone()['cnt']
    
    cursor.execute("SELECT COUNT(*) as cnt FROM queues WHERE queue_type = 'M' AND status = 'waiting'")
    m_wait = cursor.fetchone()['cnt']
    
    cursor.execute("SELECT COUNT(*) as cnt FROM queues WHERE queue_type = 'L' AND status = 'waiting'")
    l_wait = cursor.fetchone()['cnt']
    
    cursor.execute("SELECT COUNT(*) as cnt FROM queues WHERE queue_type = 'VIP' AND status = 'waiting'")
    vip_wait = cursor.fetchone()['cnt']
    
    # 桌位占用情况
    cursor.execute("SELECT * FROM tables_status WHERE id = 'status'")
    tables = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
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

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 检查当前是否有排队，如果没有排队，尝试直接智能调配桌位资产（绿色通道）
    cursor.execute("SELECT COUNT(*) as cnt FROM queues WHERE queue_type = %s AND status = 'waiting'", (q_type,))
    current_wait = cursor.fetchone()['cnt']
    
    if current_wait == 0:
        cursor.execute("SELECT * FROM tables_status WHERE id = 'status'")
        tables = cursor.fetchone()
        allocated = False
        alloc_msg = ""

        if party_size <= 2:
            if tables["S"] < 4:
                cursor.execute("UPDATE tables_status SET S = S + 1 WHERE id = 'status'")
                allocated = True; alloc_msg = "分配成功：[标准小桌]"
            elif tables["M"] < 3:
                cursor.execute("UPDATE tables_status SET M = M + 1 WHERE id = 'status'")
                allocated = True; alloc_msg = "小桌爆满，升级指派：[中桌]"
            elif tables["L"] < 2:
                cursor.execute("UPDATE tables_status SET L = L + 1 WHERE id = 'status'")
                allocated = True; alloc_msg = "极度紧张，特殊放行：[大桌]"
        elif 3 <= party_size <= 4:
            if tables["M"] < 3:
                cursor.execute("UPDATE tables_status SET M = M + 1 WHERE id = 'status'")
                allocated = True; alloc_msg = "分配成功：[标准中桌]"
            elif tables["L"] < 2:
                cursor.execute("UPDATE tables_status SET L = L + 1 WHERE id = 'status'")
                allocated = True; alloc_msg = "中桌爆满，升级指派：[大桌]"
        else:
            if tables["L"] < 2:
                cursor.execute("UPDATE tables_status SET L = L + 1 WHERE id = 'status'")
                allocated = True; alloc_msg = "分配成功：[标准大桌]"

        if allocated:
            # 扣减成功，直接放行，更新全局总数
            cursor.execute("UPDATE counters SET total_tickets = total_tickets + 1, total_served = total_served + 1 WHERE id = 'ticket_counters'")
            conn.commit()
            cursor.close()
            conn.close()
            broadcast_screen_update()
            return jsonify({
                "status": "green_channel",
                "message": f"欢迎您，{customer_name}！店内当前有空闲桌位，已为您开启免排队绿色通道直接就餐！",
                "alloc_msg": alloc_msg
            })

    # 必须进入常规排队流程 - 获取并更新计数器
    cursor.execute(f"SELECT {q_type} FROM counters WHERE id = 'ticket_counters'")
    current_num = cursor.fetchone()[q_type]
    cursor.execute(f"UPDATE counters SET {q_type} = {q_type} + 1, total_tickets = total_tickets + 1 WHERE id = 'ticket_counters'")
    
    ticket_num = f"{prefix}{current_num:03d}"

    # 写入排队表
    cursor.execute("""
        INSERT INTO queues (ticket_num, customer_name, party_size, queue_type, status, timestamp)
        VALUES (%s, %s, %s, %s, 'waiting', %s)
    """, (ticket_num, customer_name, party_size, q_type, time.time()))
    
    conn.commit()
    cursor.close()
    conn.close()

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
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 叫号优先级：VIP -> S -> M -> L
    next_customer = None
    for q_type in ["VIP", "S", "M", "L"]:
        cursor.execute("""
            SELECT * FROM queues 
            WHERE queue_type = %s AND status = 'waiting'
            ORDER BY timestamp ASC LIMIT 1
        """, (q_type,))
        next_customer = cursor.fetchone()
        if next_customer:
            break

    if not next_customer:
        cursor.close()
        conn.close()
        return jsonify({"status": "empty", "message": "当前排队队列中没有正在等待的顾客。"})

    party_size = next_customer["party_size"]
    cursor.execute("SELECT * FROM tables_status WHERE id = 'status'")
    tables = cursor.fetchone()
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
        if tables["L"] < 2:
            table_field = "L"

    if not table_field:
        cursor.close()
        conn.close()
        return jsonify({"status": "full",
                        "message": f"呼叫失败！全店对应物理桌位已饱和，无法安置 {next_customer['ticket_num']} 号，请先释放餐桌资产。"}), 400

    # 改变状态，更新资产
    cursor.execute("UPDATE queues SET status = 'served' WHERE id = %s", (next_customer["id"],))
    cursor.execute(f"UPDATE tables_status SET {table_field} = {table_field} + 1 WHERE id = 'status'")
    cursor.execute("UPDATE counters SET total_served = total_served + 1 WHERE id = 'ticket_counters'")

    conn.commit()

    # 顺便读取当前堆顶最危急的食材，为商家提供 AI 推销话术
    cursor.execute("SELECT * FROM inventory ORDER BY expiry_days ASC LIMIT 1")
    top_ing = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    ai_tip = "💡 智策看板：店内库存储备充沛健康。"
    if top_ing:
        if top_ing["expiry_days"] <= 0:
            ai_tip = f"❌ 智策预警：【{top_ing['name']}】已过期，请前往库存页面一键报废销毁！"
        elif top_ing["expiry_days"] <= 2:
            ai_tip = f"🔊 智策智能推介：食材【{top_ing['name']}】还有 {top_ing['expiry_days']} 天临期！建议本次带位时让服务员进行强力主推促销！"

    broadcast_screen_update()

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
    
    if not table_type or table_type not in ["S", "M", "L"]:
        return jsonify({"status": "error", "message": "桌位类型不合规"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM tables_status WHERE id = 'status'")
    tables = cursor.fetchone()

    if tables.get(table_type, 0) <= 0:
        cursor.close()
        conn.close()
        return jsonify({"status": "error", "message": "该类型桌位当前未被占用，无需释放！"}), 400

    cursor.execute(f"UPDATE tables_status SET {table_type} = {table_type} - 1 WHERE id = 'status'")
    conn.commit()
    cursor.close()
    conn.close()
    
    broadcast_screen_update()
    return jsonify({"status": "success", "message": f"成功空出 1 张 [{table_type}] 型餐桌！"})


# ==========================================
# 🍎 智策临期食材堆（Inventory CRUD + 级联消库）
# ==========================================
@app.route('/api/inventory/list', methods=['GET'])
def api_get_inventory():
    """获取通过临期天数升序排列的食材列表（映射底层最小堆逻辑）"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM inventory ORDER BY expiry_days ASC")
    items = cursor.fetchall()
    cursor.close()
    conn.close()
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

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO inventory (name, qty, unit, expiry_days)
        VALUES (%s, %s, %s, %s)
    """, (name, qty, unit, expiry_days))
    conn.commit()
    cursor.close()
    conn.close()
    
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

    if not item_id:
        return jsonify({"status": "error", "message": "缺少食材 ID"}), 400

    update_fields = []
    update_values = []
    
    if name:
        update_fields.append("name = %s")
        update_values.append(name)
    if isinstance(qty, int) and qty > 0:
        update_fields.append("qty = %s")
        update_values.append(qty)
    if unit:
        update_fields.append("unit = %s")
        update_values.append(unit)
    if isinstance(expiry_days, int):
        update_fields.append("expiry_days = %s")
        update_values.append(expiry_days)
    
    if not update_fields:
        return jsonify({"status": "error", "message": "没有需要更新的字段"}), 400
    
    update_values.append(item_id)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE inventory SET {', '.join(update_fields)} WHERE id = %s", update_values)
    conn.commit()
    
    if cursor.rowcount > 0:
        cursor.close()
        conn.close()
        return jsonify({"status": "success", "message": "修改成功！"})
    
    cursor.close()
    conn.close()
    return jsonify({"status": "error", "message": "未找到指定食材"}), 404


@app.route('/api/inventory/delete/<item_id>', methods=['DELETE'])
def api_delete_inventory(item_id):
    """直接删除某条特定数据（如手工清理、人工修正）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM inventory WHERE id = %s", (item_id,))
    conn.commit()
    
    if cursor.rowcount > 0:
        cursor.close()
        conn.close()
        return jsonify({"status": "success", "message": "指定批次已被成功移除。"})
    
    cursor.close()
    conn.close()
    return jsonify({"status": "error", "message": "删除失败，物品不存在。"}), 404


@app.route('/api/inventory/consume', methods=['POST'])
def api_consume_cascade():
    """【级联消库核心算法】管理员自主控量一键扣除"""
    data = request.json or {}
    req_qty = data.get("qty")

    if not isinstance(req_qty, int) or req_qty <= 0:
        return jsonify({"status": "error", "message": "消耗数量必须为正整数！"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 1. 查找目前堆顶最紧急的批次
    cursor.execute("SELECT * FROM inventory ORDER BY expiry_days ASC LIMIT 1")
    top_batch = cursor.fetchone()
    
    if not top_batch:
        cursor.close()
        conn.close()
        return jsonify({"status": "empty", "message": "当前库存中空空如也，无任何物料可扣减。"})

    # 2. 安全检查：如果堆顶第一批已经过期，强行阻断进行安全报废，不许扣减正常消耗
    if top_batch["expiry_days"] <= 0:
        cursor.execute("DELETE FROM inventory WHERE id = %s", (top_batch["id"],))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({
            "status": "expired_blocked",
            "message": f"🚨 智能防灾机制强行阻断！当前最紧急批次【{top_batch['name']}】已过期 {abs(top_batch['expiry_days'])} 天！系统已拒绝本次扣除请求，并自动对该批次总计 {top_batch['qty']} {top_batch['unit']} 执行【整批安全出堆报废销毁】流程！"
        })

    # 3. 级联滚动消库计算
    remaining_to_deduct = req_qty
    consumed_flow = []

    # 按到期紧急度从小到大依次遍历
    cursor.execute("SELECT * FROM inventory ORDER BY expiry_days ASC")
    all_active_batches = cursor.fetchall()

    for batch in all_active_batches:
        if remaining_to_deduct <= 0:
            break

        # 途中如果碰到过期的，则不扣除此批次，直接终止向下传播
        if batch["expiry_days"] <= 0:
            continue

        b_id = batch["id"]
        b_name = batch["name"]
        b_qty = batch["qty"]
        b_unit = batch["unit"]

        if b_qty > remaining_to_deduct:
            # 当前批次足够扣减
            cursor.execute("UPDATE inventory SET qty = qty - %s WHERE id = %s", (remaining_to_deduct, b_id))
            consumed_flow.append({"name": b_name, "qty": remaining_to_deduct, "unit": b_unit})
            remaining_to_deduct = 0
        else:
            # 当前批次不够扣，需要全额吃掉它，然后寻找下一批
            cursor.execute("DELETE FROM inventory WHERE id = %s", (b_id,))
            consumed_flow.append({"name": b_name, "qty": b_qty, "unit": b_unit})
            remaining_to_deduct -= b_qty

    conn.commit()
    cursor.close()
    conn.close()

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
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE inventory SET expiry_days = expiry_days - 1")
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"status": "success", "message": "⏳ 时空矩阵推移 1 天！全库食材生命周期缩减，已触发最小堆序列重整。"})

@app.route("/")
def home():
    return render_template("index.html")
# ==========================================
# 🚀 启动 Flask 服务
# ==========================================
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)