from flask import Flask, render_template, request, jsonify
from mysql_manager import MySQLManager

app = Flask(__name__)

db = MySQLManager()

# =========================
# 页面路由
# =========================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/user")
def user():
    return render_template("user.html")


@app.route("/admin")
def admin():
    return render_template("admin.html")


@app.route("/kuchun")
def kuchun():
    return render_template("kucun.html")


@app.route("/queue_admin")
def queue_admin():
    return render_template("queue_admin.html")


# =========================
# 取号系统
# =========================

@app.route("/api/queue/normal", methods=["POST"])
def normal_queue():

    data = request.get_json()
    people = data.get("peopleCount")

    result = db.query_one("""
        SELECT COUNT(*) AS c
        FROM queue_record
        WHERE queue_type='NORMAL'
    """)

    number = f"A{result['c'] + 1:03d}"

    db.execute("""
        INSERT INTO queue_record(queue_number, queue_type, people_count)
        VALUES(%s,%s,%s)
    """, (number, "NORMAL", people))

    return jsonify({
        "queueNumber": number,
        "type": "普通号",
        "peopleCount": people
    })


@app.route("/api/queue/vip", methods=["POST"])
def vip_queue():

    data = request.get_json()
    people = data.get("peopleCount")

    result = db.query_one("""
        SELECT COUNT(*) AS c
        FROM queue_record
        WHERE queue_type='VIP'
    """)

    number = f"VIP{result['c'] + 1:03d}"

    db.execute("""
        INSERT INTO queue_record(queue_number, queue_type, people_count)
        VALUES(%s,%s,%s)
    """, (number, "VIP", people))

    return jsonify({
        "queueNumber": number,
        "type": "VIP号",
        "peopleCount": people
    })


# =========================
# 队列管理
# =========================

@app.route("/api/queue/list")
def queue_list():

    data = db.query("""
        SELECT * FROM queue_record
        WHERE status='waiting'
        ORDER BY id ASC
    """)

    return jsonify(data)


@app.route("/api/queue/call", methods=["POST"])
def call_queue():

    vip = db.query_one("""
        SELECT * FROM queue_record
        WHERE status='waiting' AND queue_type='VIP'
        ORDER BY id ASC
        LIMIT 1
    """)

    if vip:
        db.execute("""
            UPDATE queue_record
            SET status='done'
            WHERE id=%s
        """, (vip["id"],))

        return jsonify({
            "called": vip["queue_number"],
            "type": "VIP"
        })

    normal = db.query_one("""
        SELECT * FROM queue_record
        WHERE status='waiting'
        ORDER BY id ASC
        LIMIT 1
    """)

    if normal:
        db.execute("""
            UPDATE queue_record
            SET status='done'
            WHERE id=%s
        """, (normal["id"],))

        return jsonify({
            "called": normal["queue_number"],
            "type": "NORMAL"
        })

    return jsonify({
        "called": None
    })


# =========================
# 排队管理（管理员操作）
# =========================

@app.route("/api/queue/miss/<int:id>", methods=["PUT"])
def miss_queue(id):

    db.execute("""
        UPDATE queue_record
        SET status='missed'
        WHERE id=%s
    """, (id,))

    return jsonify({"success": True})


@app.route("/api/queue/upvip/<int:id>", methods=["PUT"])
def upvip(id):

    db.execute("""
        UPDATE queue_record
        SET queue_type='VIP'
        WHERE id=%s
    """, (id,))

    return jsonify({"success": True})


@app.route("/api/queue/count")
def queue_count():

    result = db.query_one("""
        SELECT COUNT(*) AS c
        FROM queue_record
        WHERE status='waiting'
    """)

    return jsonify({
        "tables": result["c"]
    })


# =========================
# 库存系统 kuchun
# =========================

@app.route("/api/kuchun")
def get_kuchun():

    data = db.query("""
        SELECT id, food_name AS name, status
        FROM kuchun
    """)

    return jsonify(data)


@app.route("/api/kuchun/add", methods=["POST"])
def add_food():

    data = request.get_json()
    name = data.get("name")

    db.execute("""
        INSERT INTO kuchun(food_name, status)
        VALUES(%s,'normal')
    """, (name,))

    return jsonify({"success": True})


@app.route("/api/kuchun/expire/<int:id>", methods=["PUT"])
def expire_food(id):

    db.execute("""
        UPDATE kuchun
        SET status='expired'
        WHERE id=%s
    """, (id,))

    return jsonify({"success": True})


@app.route("/api/kuchun/expired", methods=["DELETE"])
def delete_expired():

    db.execute("""
        DELETE FROM kuchun
        WHERE status='expired'
    """)

    return jsonify({"success": True})


# =========================
# 启动
# =========================

if __name__ == "__main__":
    app.run(debug=True)