const BASE_URL = "/api";

async function normalQueue(peopleCount) {
    const res = await fetch(BASE_URL + "/queue/normal", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ peopleCount })
    });

    return await res.json();
}

async function vipQueue(peopleCount) {
    const res = await fetch(BASE_URL + "/queue/vip", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ peopleCount })
    });

    return await res.json();
}

async function getKuchun() {
    const res = await fetch(BASE_URL + "/kuchun");
    return await res.json();
}

async function expireFood(id) {
    const res = await fetch(BASE_URL + "/kuchun/expire/" + id, {
        method: "PUT"
    });

    return await res.json();
}

async function deleteExpiredFoods() {
    const res = await fetch(BASE_URL + "/kuchun/expired", {
        method: "DELETE"
    });

    return await res.json();
}

async function getQueueCount() {
    const res = await fetch("/api/queue/count");
    return await res.json();
}