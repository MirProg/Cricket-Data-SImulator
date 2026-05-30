document.addEventListener("DOMContentLoaded", () => {
    // Navigation
    const navBtns = document.querySelectorAll(".nav-btn");
    const views = document.querySelectorAll(".view");

    navBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            navBtns.forEach(b => b.classList.remove("active"));
            views.forEach(v => v.style.display = "none");
            
            btn.classList.add("active");
            document.getElementById(btn.dataset.target + "-view").style.display = "flex";
        });
    });

    // Load Teams
    async function loadTeams() {
        try {
            const response = await fetch("/api/teams");
            const teams = await response.json();
            
            const t1Select = document.getElementById("team1-select");
            const t2Select = document.getElementById("team2-select");
            
            t1Select.innerHTML = "";
            t2Select.innerHTML = "";
            
            teams.forEach(t => {
                t1Select.innerHTML += `<option value="${t.id}">${t.name}</option>`;
                t2Select.innerHTML += `<option value="${t.id}">${t.name}</option>`;
            });

            // If we have teams, set default to IND and AUS if they exist
            if (teams.find(t => t.id === "6")) t1Select.value = "6";
            if (teams.find(t => t.id === "2")) t2Select.value = "2";

        } catch (error) {
            console.error("Error loading teams:", error);
        }
    }
    
    loadTeams();

    // Simulation logic
    const startBtn = document.getElementById("start-sim-btn");
    let ws = null;

    startBtn.addEventListener("click", () => {
        const t1 = document.getElementById("team1-select").value;
        const t2 = document.getElementById("team2-select").value;
        const format = document.getElementById("format-select").value;
        
        const commBox = document.getElementById("commentary-box");
        commBox.innerHTML = '<div class="commentary-item system">Connecting to AI Engine...</div>';

        if (ws) {
            ws.close();
        }

        ws = new WebSocket(`ws://${window.location.host}/ws/simulate`);
        
        ws.onopen = () => {
            ws.send(JSON.stringify({ team1: t1, team2: t2, format: format }));
            startBtn.disabled = true;
            startBtn.textContent = "Simulating...";
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            if (data.type === "info") {
                document.getElementById("match-status").textContent = data.message;
            } else if (data.type === "ball") {
                // Update Score
                document.getElementById("score-team1").querySelector(".score").textContent = data.t1_score;
                document.getElementById("score-team1").querySelector(".overs").textContent = `(${data.t1_overs})`;
                
                document.getElementById("score-team2").querySelector(".score").textContent = data.t2_score;
                document.getElementById("score-team2").querySelector(".overs").textContent = `(${data.t2_overs})`;
                
                // Add Commentary
                const cDiv = document.createElement("div");
                cDiv.className = `commentary-item ${data.event_class}`;
                cDiv.innerHTML = `<span class="ball">${data.over_ball}</span> ${data.commentary}`;
                commBox.prepend(cDiv);
            } else if (data.type === "result") {
                document.getElementById("match-status").textContent = data.result;
                const cDiv = document.createElement("div");
                cDiv.className = `commentary-item system`;
                cDiv.innerHTML = `<strong>MATCH COMPLETE:</strong> ${data.result}`;
                commBox.prepend(cDiv);
                
                startBtn.disabled = false;
                startBtn.textContent = "Simulate Match";
            } else if (data.type === "error") {
                alert(data.message);
                startBtn.disabled = false;
                startBtn.textContent = "Simulate Match";
            }
        };

        ws.onclose = () => {
            startBtn.disabled = false;
            startBtn.textContent = "Simulate Match";
        };
    });
});
