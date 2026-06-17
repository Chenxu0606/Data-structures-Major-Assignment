// ==========================================
// ⚙️ 全局配置与状态
// ==========================================
const API_BASE = 'http://localhost:5000/api';
// 建立全局 WebSocket 连接，接管服务端的大屏广播
const socket = io('http://localhost:5000');

// 监听后端推送的快照，动态更新大屏数据
socket.on('screen_sync', (data) => {
    updateDashboardUI(data);
});

// ==========================================
// 🛣️ SPA 视图路由系统 (原生 JS DOM 控制)
// ==========================================
function switchView(viewId) {
    document.querySelectorAll('.view-section').forEach(el => el.classList.remove('active'));
    document.getElementById(viewId).classList.add('active');

    // 如果切到了库存页，自动请求一次数据
    if(viewId === 'view-inventory') {
        fetchInventoryList();
    }
}

// 密码弹窗逻辑
function showPasswordModal() { document.getElementById('auth-modal').classList.add('active'); }
function closeModal() { document.getElementById('auth-modal').classList.remove('active'); }
function verifyPassword() {
    const pwd = document.getElementById('admin-pwd').value;
    if (pwd === 'admin') {
        closeModal();
        switchView('view-merchant'); // 验证成功进入商家后台
    } else {
        alert('❌ 验证失败：管理密码错误！');
    }
}

// ==========================================
// 👨‍👩‍👧‍👦 页面 2：自助取号功能
// ==========================================
async function takeTicket(isVip) {
    const name = document.getElementById('cust-name').value.trim();
    const size = parseInt(document.getElementById('cust-size').value);

    if (!name || isNaN(size) || size <= 0) {
        alert('⚠️ 请完整填写正确的姓名和就餐人数！'); return;
    }

    try {
        const res = await fetch(`${API_BASE}/queue/enqueue`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ customer_name: name, party_size: size, is_vip: isVip })
        });
        const result = await res.json();

        if (result.status === 'green_channel') {
            alert(`🎉 绿通放行！\n${result.message}\n${result.alloc_msg}`);
        } else if (result.status === 'queued') {
            alert(`🎫 取号成功！您的号码：${result.ticket_num}\n对应桌型：${result.display_name}`);
        }

        // 清空表单
        document.getElementById('cust-name').value = '';
        document.getElementById('cust-size').value = '';
    } catch (err) {
        alert('网络通信失败，请检查后端 Python 服务是否开启。');
    }
}

// 渲染大屏数据
function updateDashboardUI(data) {
    // 渲染 KPI 数据
    document.getElementById('kpi-total').innerText = data.kpi.total_tickets;
    document.getElementById('kpi-served').innerText = data.kpi.total_served;
    document.getElementById('kpi-wait').innerText = data.kpi.total_wait;

    // 渲染排队详情
    document.getElementById('q-s').innerText = data.queues.S_len;
    document.getElementById('q-m').innerText = data.queues.M_len;
    document.getElementById('q-l').innerText = data.queues.L_len;
    document.getElementById('q-vip').innerText = data.queues.VIP_len;

    // 同步渲染商家后台的实体桌位占用情况
    document.getElementById('tbl-s').innerText = `${data.tables.occupied_s}/${data.tables.total_s}`;
    document.getElementById('tbl-m').innerText = `${data.tables.occupied_m}/${data.tables.total_m}`;
    document.getElementById('tbl-l').innerText = `${data.tables.occupied_l}/${data.tables.total_l}`;
}

// 初次加载时拉取一次静态快照
fetch(`${API_BASE}/queue/snapshot`).then(r => r.json()).then(updateDashboardUI).catch(console.error);

// ==========================================
// 📢 页面 3：商家核心调度系统
// ==========================================
async function callNextCustomer() {
    try {
        const res = await fetch(`${API_BASE}/queue/call`, { method: 'POST' });
        const result = await res.json();

        if (result.status === 'success') {
            // 更新商家雷达的呼叫日志
            document.getElementById('ai-call-log').innerText = `✅ 成功调度：请 ${result.ticket_num} 号 (${result.customer_name}) 进店就餐！`;
            // 更新智能推销话术
            document.getElementById('ai-tip-log').innerText = result.ai_tip;
        } else {
            alert(result.message); // 可能是队列空，或者满座无物理资源
        }
    } catch (err) { console.error(err); }
}

async function releaseTable(tableType) {
    try {
        const res = await fetch(`${API_BASE}/queue/release`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ table_type: tableType })
        });
        const result = await res.json();
        alert(result.message);
    } catch (err) { console.error(err); }
}

// ==========================================
// 🍎 页面 4：智策底层库存最小堆控制
// ==========================================
async function fetchInventoryList() {
    try {
        const res = await fetch(`${API_BASE}/inventory/list`);
        const data = await res.json();
        const listDiv = document.getElementById('inventory-list');
        listDiv.innerHTML = ''; // 清空重新渲染

        if (data.inventory.length === 0) {
            listDiv.innerHTML = '<p style="color:gray; text-align:center;">（目前仓库空空如也）</p>';
            return;
        }

        data.inventory.forEach(item => {
            let statusTag = '';
            let cssClass = 'tag-safe';
            if (item.expiry_days <= 0) { statusTag = `[已过期 ${Math.abs(item.expiry_days)}天]`; cssClass = 'tag-danger'; }
            else if (item.expiry_days <= 2) { statusTag = `[临期 ${item.expiry_days}天]`; cssClass = 'tag-warn'; }
            else { statusTag = `[新鲜 ${item.expiry_days}天]`; }

            const div = document.createElement('div');
            div.className = 'inv-item';
            div.innerHTML = `
                <span class="${cssClass}">${statusTag} ${item.name}</span>
                <span><strong>${item.qty}</strong> ${item.unit}</span>
            `;
            listDiv.appendChild(div);
        });
    } catch (err) { console.error(err); }
}

async function addInventory() {
    const name = document.getElementById('inv-name').value.trim();
    const qty = parseInt(document.getElementById('inv-qty').value);
    const unit = document.getElementById('inv-unit').value.trim();
    const days = parseInt(document.getElementById('inv-days').value);

    if (!name || isNaN(qty) || !unit || isNaN(days)) { alert('请填写完整规范的入库参数！'); return; }

    try {
        const res = await fetch(`${API_BASE}/inventory/add`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name, qty: qty, unit: unit, expiry_days: days })
        });
        const result = await res.json();
        alert(result.message);

        // 清空表单并刷新列表
        document.getElementById('inv-name').value = '';
        document.getElementById('inv-qty').value = '';
        document.getElementById('inv-unit').value = '';
        document.getElementById('inv-days').value = '';
        fetchInventoryList();
    } catch (err) { console.error(err); }
}

async function consumeInventory() {
    const qty = parseInt(document.getElementById('consume-qty').value);
    if (isNaN(qty) || qty <= 0) { alert('消耗数量必须为合法的正整数！'); return; }

    try {
        const res = await fetch(`${API_BASE}/inventory/consume`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ qty: qty })
        });
        const result = await res.json();

        // 拼接后台执行的级联流水信息
        let msg = result.message;
        if (result.flow && result.flow.length > 0) {
            msg += '\n\n底层级联流水日志：\n' + result.flow.map(f => `• 消耗【${f.name}】: ${f.qty} ${f.unit}`).join('\n');
        }
        alert(msg);
        fetchInventoryList(); // 重新拉取最新的堆数据
    } catch (err) { console.error(err); }
}

async function simulateTimePass() {
    try {
        const res = await fetch(`${API_BASE}/inventory/time_pass`, { method: 'POST' });
        const result = await res.json();
        alert(result.message);
        fetchInventoryList();
    } catch (err) { console.error(err); }
}