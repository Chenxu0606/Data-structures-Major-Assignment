// ==========================================
// ⚙️ ZHICE AI Dashboard - Clean JS Core
// ==========================================

const socket = io();

// =====================
// 📦 状态中心
// =====================
const state = {
    queue: {
        total: 0,
        served: 0,
        wait: 0,
        small: 0,
        mid: 0,
        large: 0,
        vip: 0
    },

    tables: {
        S: { used: 0, total: 4 },
        M: { used: 0, total: 3 },
        L: { used: 0, total: 2 }
    },

    inventory: []
};

// =====================
// 🎯 DOM 缓存
// =====================
const $ = (id) => document.getElementById(id);

const DOM = {
    modal: $("auth-modal"),

    kpiTotal: $("kpi-total"),
    kpiServed: $("kpi-served"),
    kpiWait: $("kpi-wait"),

    qS: $("q-s"),
    qM: $("q-m"),
    qL: $("q-l"),
    qVip: $("q-vip"),

    tblS: $("tbl-s"),
    tblM: $("tbl-m"),
    tblL: $("tbl-l"),

    invList: $("inventory-list"),
    aiCall: $("ai-call-log"),
    aiTip: $("ai-tip-log")
};

// =====================
// 🧭 页面切换
// =====================
function switchView(viewId) {
    document.querySelectorAll(".view-section")
        .forEach(v => v.classList.remove("active"));

    const el = document.getElementById(viewId);
    if (el) el.classList.add("active");
}

// =====================
// 🔐 登录弹窗
// =====================
function showPasswordModal() {
    DOM.modal.style.display = "flex";
}

function closeModal() {
    DOM.modal.style.display = "none";
}

function verifyPassword() {
    const pwd = $("admin-pwd").value;

    if (pwd === "admin") {
        closeModal();
        switchView("view-merchant");
    } else {
        alert("密码错误");
    }
}

// =====================
// 🎫 取号
// =====================
function takeTicket(vip = false) {
    const name = $("cust-name").value;
    const size = parseInt($("cust-size").value || 0);

    if (!name || !size) {
        alert("请输入信息");
        return;
    }

    state.queue.total++;

    if (vip) state.queue.vip++;

    if (size <= 2) state.queue.small++;
    else if (size <= 4) state.queue.mid++;
    else state.queue.large++;

    updateQueueUI();

    socket.emit("new_ticket", { name, size, vip });
}

// =====================
// 📞 呼叫下一位
// =====================
function callNextCustomer() {
    socket.emit("call_next");

    state.queue.served++;

    state.queue.wait =
        Math.max(0, state.queue.total - state.queue.served);

    updateQueueUI();

    logAI("呼叫下一位顾客");
}

// =====================
// 🪑 释放桌位
// =====================
function releaseTable(type) {
    const t = state.tables[type];
    if (t.used > 0) t.used--;

    updateTableUI();

    socket.emit("release_table", { type });
}

// =====================
// 📊 Queue UI
// =====================
function updateQueueUI() {
    DOM.kpiTotal.textContent = state.queue.total;
    DOM.kpiServed.textContent = state.queue.served;
    DOM.kpiWait.textContent =
        state.queue.total - state.queue.served;

    DOM.qS.textContent = state.queue.small;
    DOM.qM.textContent = state.queue.mid;
    DOM.qL.textContent = state.queue.large;
    DOM.qVip.textContent = state.queue.vip;
}

// =====================
// 🪑 Table UI
// =====================
function updateTableUI() {
    DOM.tblS.textContent =
        `${state.tables.S.used}/${state.tables.S.total}`;

    DOM.tblM.textContent =
        `${state.tables.M.used}/${state.tables.M.total}`;

    DOM.tblL.textContent =
        `${state.tables.L.used}/${state.tables.L.total}`;
}

// =====================
// 📢 AI Log
// =====================
function logAI(msg) {
    const time = new Date().toLocaleTimeString();

    DOM.aiCall.innerHTML =
        `[${time}] ${msg}<br>` + DOM.aiCall.innerHTML;
}

function setAITip(msg) {
    DOM.aiTip.innerHTML = msg;
}

// =====================
// 📦 库存
// =====================
function addInventory() {
    const name = $("inv-name").value;
    const qty = parseInt($("inv-qty").value || 0);
    const unit = $("inv-unit").value;
    const days = parseInt($("inv-days").value || 0);

    if (!name || !qty) return alert("输入不完整");

    state.inventory.push({ name, qty, unit, daysLeft: days });

    renderInventory();
}

function renderInventory() {
    DOM.invList.innerHTML = "";

    state.inventory.forEach((item, i) => {
        const div = document.createElement("div");
        div.className = "inv-item";

        div.innerHTML = `
            <div>
                <strong>${item.name}</strong>
                <span>${item.qty} ${item.unit}</span>
            </div>
            <div>
                剩余 ${item.daysLeft} 天
                <button onclick="removeInventory(${i})">删除</button>
            </div>
        `;

        DOM.invList.appendChild(div);
    });
}

function removeInventory(i) {
    state.inventory.splice(i, 1);
    renderInventory();
}

// =====================
// ⏳ 模拟时间
// =====================
function simulateTimePass() {
    state.inventory.forEach(i => i.daysLeft--);
    renderInventory();
}

// =====================
// 🧹 消耗库存
// =====================
function consumeInventory() {
    const qty = parseInt($("consume-qty").value || 1);

    if (!state.inventory.length) return;

    state.inventory[0].qty -= qty;

    if (state.inventory[0].qty <= 0) {
        state.inventory.shift();
    }

    renderInventory();
}

// =====================
// 🔌 Socket
// =====================
socket.on("queue_update", (data) => {
    Object.assign(state.queue, data);
    updateQueueUI();
});

socket.on("ai_tip", (data) => {
    setAITip(data.tip);
});

// =====================
// 🚀 初始化
// =====================
function init() {
    updateQueueUI();
    updateTableUI();
}

document.addEventListener("DOMContentLoaded", init);