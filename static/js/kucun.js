window.onload = loadFoods;

async function loadFoods() {

    const foods = await getKuchun();

    const box = document.getElementById("foodList");

    box.innerHTML = "";

    foods.forEach(item => {

        const div = document.createElement("div");

        div.style.display = "flex";
        div.style.justifyContent = "space-between";
        div.style.padding = "10px";
        div.style.margin = "8px 0";
        div.style.background = "#f6f6f6";
        div.style.borderRadius = "10px";

        div.innerHTML = `
            <div>
                <b>${item.name}</b>
                <span style="margin-left:10px;color:${item.status === 'expired' ? 'red' : 'green'}">
                    ${item.status}
                </span>
            </div>

            <button onclick="expire(${item.id})">
                标记过期
            </button>
        `;

        box.appendChild(div);
    });
}

async function expire(id) {
    await expireFood(id);
    loadFoods();
}

async function deleteExpiredFoods() {
    await deleteExpired();
    loadFoods();
}

async function addFood() {

    const name = document.getElementById("foodName").value;

    if (!name) {
        alert("请输入食材");
        return;
    }

    await fetch("/api/kuchun/add", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({name})
    });

    document.getElementById("foodName").value = "";

    loadFoods();
}