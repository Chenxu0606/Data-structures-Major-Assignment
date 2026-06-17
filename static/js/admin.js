async function load(){
    let d=await fetch("/api/queue/list").then(r=>r.json());
    let box=document.getElementById("queueList");
    box.innerHTML="";
    d.forEach(i=>{
        let div=document.createElement("div");
        div.innerText=i.queue_number+"-"+i.queue_type;
        box.appendChild(div);
    });
}

async function callQueue(){
    let r=await fetch("/api/queue/call",{method:"POST"}).then(r=>r.json());
    document.getElementById("callingText").innerText=r.called||"暂无";
    load();
}

setInterval(load,3000);
window.onload=load;