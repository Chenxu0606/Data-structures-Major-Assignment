const API = {
    async request(url, method = 'GET', data = null) {
        const options = { method, headers: { 'Content-Type': 'application/json' } };
        if (data) options.body = JSON.stringify(data);
        try {
            const response = await fetch(url, options);
            return await response.json();
        } catch (error) {
            console.error('通信异常:', error);
            showToast('服务器连接失败');
        }
    },
    // 排队
    takeQueue(type, peopleCount) { return this.request('/api/queue/take', 'POST', { type, people_count: peopleCount }); },
    getQueueList() { return this.request('/api/queue/list', 'GET'); },
    operateQueue(id, action) { return this.request('/api/queue/operate', 'POST', { id, action }); },
    // 库存
    getKucunList() { return this.request('/api/kucun/list', 'GET'); },
    addKucun(foodName, expireDate) { return this.request('/api/kucun/add', 'POST', { food_name: foodName, expire_date: expireDate }); },
    deleteKucun(id) { return this.request('/api/kucun/delete', 'POST', { id }); },
    clearExpired() { return this.request('/api/kucun/clear_expired', 'POST'); }
};

function showToast(message) {
    let toast = document.getElementById('toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'toast';
        toast.className = 'toast';
        document.body.appendChild(toast);
    }
    toast.innerText = message;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 2000);
}