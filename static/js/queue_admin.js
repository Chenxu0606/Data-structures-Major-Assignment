async function load(){
    let d=await fetch("/api/queue/list").then(r=>r.json());
    let box=document.getElementById("queueList");
    box.innerHTML="";
    d.forEach(i=>{
        let div=document.createElement("div");
        div.innerHTML=i.queue_number+
        `<button onclick="vip(${i.id})">插VIP</button>
         <button onclick="miss(${i.id})">过号</button>`;
        box.appendChild(div);
    });
}

async function vip(id){
    await fetch("/api/queue/upvip/"+id,{method:"PUT"});
    load();
}

async function miss(id){
    await fetch("/api/queue/miss/"+id,{method:"PUT"});
    load();
}

setInterval(load,3000);
window.onload=load;