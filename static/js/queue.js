async function normalQueue() {

    const peopleCount = document.getElementById("peopleCount").value;

    if (!peopleCount || peopleCount <= 0) {
        alert("请输入正确人数");
        return;
    }

    const res = await normalQueueAPI(Number(peopleCount));

    showResult(res);
}

async function vipQueue() {

    const peopleCount = document.getElementById("peopleCount").value;

    if (!peopleCount || peopleCount <= 0) {
        alert("请输入正确人数");
        return;
    }

    const res = await vipQueueAPI(Number(peopleCount));

    showResult(res);
}

function showResult(res) {

    document.getElementById("resultBox").style.display = "block";

    document.getElementById("queueNumber").innerText =
        "号码：" + res.queueNumber;

    document.getElementById("queueType").innerText =
        "类型：" + res.type;

    document.getElementById("peopleCountShow").innerText =
        "人数：" + res.peopleCount + "人";
}