document.addEventListener("DOMContentLoaded", () => {
    // Navigation Tab Switching
    const navBtns = document.querySelectorAll(".nav-btn");
    const views = document.querySelectorAll(".view");

    navBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            navBtns.forEach(b => b.classList.remove("active"));
            views.forEach(v => {
                v.style.display = "none";
                v.classList.remove("active");
            });
            
            btn.classList.add("active");
            const targetView = document.getElementById(btn.dataset.target + "-view");
            targetView.style.display = btn.dataset.target === "matches" || btn.dataset.target === "players" || btn.dataset.target === "records" ? "flex" : "block";
            targetView.classList.add("active");
            
            // Trigger specific view load callbacks
            if (btn.dataset.target === "dashboard") {
                loadDashboardStats();
            } else if (btn.dataset.target === "matches") {
                loadMatchesList();
            } else if (btn.dataset.target === "records") {
                loadLeaderboards();
            }
        });
    });

    // 1. DASHBOARD LOAD STATS
    async function loadDashboardStats() {
        try {
            const response = await fetch("/api/v1/db/stats");
            const stats = await response.json();
            if (stats.error) return;
            document.getElementById("db-stat-matches").textContent = stats.matches.toLocaleString();
            document.getElementById("db-stat-players").textContent = stats.players.toLocaleString();
            document.getElementById("db-stat-teams").textContent = stats.teams.toLocaleString();
            document.getElementById("db-stat-tournaments").textContent = stats.tournaments.toLocaleString();
        } catch (error) {
            console.error("Error loading dashboard stats:", error);
        }
    }
    loadDashboardStats(); // Load on start

    // 2. LOAD TEAMS FOR DROPDOWNS
    async function loadTeamsDropdown() {
        try {
            // Simulator Teams (ESPN domestic / Cricsheet)
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

            if (teams.find(t => t.id === "6")) t1Select.value = "6";
            if (teams.find(t => t.id === "2")) t2Select.value = "2";

            // CA Scorecards Filter Teams
            const caResponse = await fetch("/api/v1/ca/teams");
            const caTeams = await caResponse.json();
            const caTeamFilter = document.getElementById("match-filter-team");
            caTeamFilter.innerHTML = '<option value="">All Teams</option>';
            caTeams.forEach(t => {
                caTeamFilter.innerHTML += `<option value="${t.team_id}">${t.name}</option>`;
            });
        } catch (error) {
            console.error("Error loading dropdown teams:", error);
        }
    }
    loadTeamsDropdown();

    // 3. MATCHES BROWSER PAGINATION & SEARCH
    let matchLimit = 15;
    let matchOffset = 0;

    const applyFiltersBtn = document.getElementById("apply-filters-btn");
    if (applyFiltersBtn) {
        applyFiltersBtn.addEventListener("click", () => {
            matchOffset = 0;
            loadMatchesList();
        });
    }

    async function loadMatchesList() {
        const format = document.getElementById("match-filter-format").value;
        const team = document.getElementById("match-filter-team").value;
        const year = document.getElementById("match-filter-year").value;
        const search = document.getElementById("match-filter-search").value;

        let url = `/api/v1/ca/matches?limit=${matchLimit}&offset=${matchOffset}`;
        if (format) url += `&format_filter=${encodeURIComponent(format)}`;
        if (team) url += `&team_id=${encodeURIComponent(team)}`;
        if (year) url += `&year=${encodeURIComponent(year)}`;
        if (search) url += `&search=${encodeURIComponent(search)}`;

        const container = document.getElementById("matches-list-container");
        container.innerHTML = '<div class="info-text">Loading matches list...</div>';

        try {
            const res = await fetch(url);
            const data = await res.json();
            if (data.error) {
                container.innerHTML = `<div class="error-text">Failed to load matches: ${data.error}</div>`;
                return;
            }

            document.getElementById("matches-total-count").textContent = `Showing ${data.matches.length} of ${data.total} matches`;

            if (data.matches.length === 0) {
                container.innerHTML = '<div class="info-text">No matches found matching the criteria.</div>';
                document.getElementById("matches-pagination").innerHTML = "";
                return;
            }

            container.innerHTML = "";
            data.matches.forEach(m => {
                const card = document.createElement("div");
                card.className = "match-card";
                card.addEventListener("click", () => showScorecard(m.match_id));

                const formatClass = m.format ? m.format.toLowerCase().replace(' ', '-') : 'other';
                
                // Highlight winner
                let t1Class = "";
                let t2Class = "";
                if (m.result) {
                    if (m.result.includes(m.team1_name)) {
                        t1Class = "winner";
                    } else if (m.result.includes(m.team2_name)) {
                        t2Class = "winner";
                    }
                }

                card.innerHTML = `
                    <div class="match-card-header">
                        <span class="match-format-badge ${formatClass}">${m.format || 'Other'}</span>
                        <span class="match-date">${m.date || ''}</span>
                    </div>
                    <div class="match-card-teams">
                        <span class="${t1Class}">🏏 ${m.team1_name || 'Team 1'}</span>
                        <span class="${t2Class}">🏏 ${m.team2_name || 'Team 2'}</span>
                    </div>
                    <div class="match-card-venue">${m.venue || ''}</div>
                    <div class="match-card-result">${m.result || 'No result description'}</div>
                `;
                container.appendChild(card);
            });

            renderPagination(data.total);

        } catch (error) {
            console.error("Error loading matches:", error);
            container.innerHTML = '<div class="error-text">Error fetching matches.</div>';
        }
    }

    function renderPagination(total) {
        const pagContainer = document.getElementById("matches-pagination");
        pagContainer.innerHTML = "";

        const totalPages = Math.ceil(total / matchLimit);
        const currentPage = Math.floor(matchOffset / matchLimit) + 1;

        if (totalPages <= 1) return;

        // Prev button
        const prevBtn = document.createElement("button");
        prevBtn.className = "page-btn";
        prevBtn.textContent = "«";
        prevBtn.disabled = currentPage === 1;
        prevBtn.addEventListener("click", () => {
            matchOffset = (currentPage - 2) * matchLimit;
            loadMatchesList();
        });
        pagContainer.appendChild(prevBtn);

        // Show page range
        let startPage = Math.max(1, currentPage - 2);
        let endPage = Math.min(totalPages, currentPage + 2);

        for (let p = startPage; p <= endPage; p++) {
            const pageBtn = document.createElement("button");
            pageBtn.className = `page-btn ${p === currentPage ? 'active' : ''}`;
            pageBtn.textContent = p;
            pageBtn.addEventListener("click", () => {
                matchOffset = (p - 1) * matchLimit;
                loadMatchesList();
            });
            pagContainer.appendChild(pageBtn);
        }

        // Next button
        const nextBtn = document.createElement("button");
        nextBtn.className = "page-btn";
        nextBtn.textContent = "»";
        nextBtn.disabled = currentPage === totalPages;
        nextBtn.addEventListener("click", () => {
            matchOffset = currentPage * matchLimit;
            loadMatchesList();
        });
        pagContainer.appendChild(nextBtn);
    }

    // 4. DETAILED SCORECARD MODAL POPUP
    const modal = document.getElementById("scorecard-modal");
    const closeModalBtn = document.getElementById("close-modal-btn");
    if (closeModalBtn) {
        closeModalBtn.addEventListener("click", () => modal.style.display = "none");
    }
    window.addEventListener("click", (e) => {
        if (e.target === modal) modal.style.display = "none";
    });

    async function showScorecard(matchId) {
        modal.style.display = "flex";
        const body = document.getElementById("modal-match-body");
        body.innerHTML = '<div class="info-text">Loading detailed scorecard...</div>';
        document.getElementById("modal-match-title").textContent = "Scorecard Loading...";

        try {
            const response = await fetch(`/api/v1/ca/matches/${matchId}`);
            const data = await response.json();
            if (data.error) {
                body.innerHTML = `<div class="error-text">Error: ${data.error}</div>`;
                return;
            }

            document.getElementById("modal-match-title").textContent = data.title || "Match Scorecard";

            let html = `
                <div class="scorecard-meta-block">
                    <div><span class="label">Format</span><span class="val">${data.format || 'Other'}</span></div>
                    <div><span class="label">Date</span><span class="val">${data.date || 'Unknown'}</span></div>
                    <div><span class="label">Venue</span><span class="val">${data.venue || 'Unknown'}</span></div>
                    <div><span class="label">Toss</span><span class="val">${data.toss_decision ? (data.toss_winner_id === data.team1_id ? data.team1_name : data.team2_name) + ' opted to ' + data.toss_decision : 'Unknown'}</span></div>
                </div>
            `;

            // Render Innings
            data.innings.forEach(inn => {
                html += `
                    <div class="innings-block">
                        <header class="innings-header">
                            <h3>${inn.batting_team_name} Innings</h3>
                            <span class="total">${inn.runs}/${inn.wickets} <small>(${inn.overs} ov)</small></span>
                        </header>
                        
                        <div class="innings-body">
                            <h4>Batting</h4>
                            <table class="data-table tiny">
                                <thead>
                                    <tr>
                                        <th>Batter</th>
                                        <th>Dismissal</th>
                                        <th style="text-align: right;">Runs</th>
                                        <th style="text-align: right;">Balls</th>
                                        <th style="text-align: right;">4s</th>
                                        <th style="text-align: right;">6s</th>
                                        <th style="text-align: right;">Dots</th>
                                        <th style="text-align: right;">SR</th>
                                    </tr>
                                </thead>
                                <tbody>
                `;

                inn.batting.forEach(bat => {
                    html += `
                        <tr>
                            <td><strong style="color:var(--secondary);">${bat.player_name}</strong></td>
                            <td style="color:var(--text-muted); font-style: italic;">${bat.dismissal_text || 'not out'}</td>
                            <td class="val">${bat.runs}</td>
                            <td class="val">${bat.balls}</td>
                            <td class="val">${bat.fours}</td>
                            <td class="val">${bat.sixes}</td>
                            <td class="val">${bat.dots}</td>
                            <td class="val">${bat.strike_rate ? bat.strike_rate.toFixed(2) : '-'}</td>
                        </tr>
                    `;
                });

                // Extras and Totals Rows
                html += `
                                    <tr style="border-top:1px solid var(--glass-border); font-weight:600;">
                                        <td>Extras</td>
                                        <td style="color:var(--text-muted);">${inn.extras_b}b, ${inn.extras_lb}lb, ${inn.extras_nb}nb, ${inn.extras_wd}wd</td>
                                        <td class="val">${inn.extras_total}</td>
                                        <td colspan="5"></td>
                                    </tr>
                                    <tr style="font-weight:700; font-size:1.05rem; background:rgba(255,255,255,0.02);">
                                        <td>Total</td>
                                        <td>${inn.wickets} wickets, closed innings</td>
                                        <td class="val" style="color:var(--primary);">${inn.runs}</td>
                                        <td colspan="5"></td>
                                    </tr>
                                </tbody>
                            </table>

                            <h4 style="margin-top:1rem;">Bowling</h4>
                            <table class="data-table tiny">
                                <thead>
                                    <tr>
                                        <th>Bowler</th>
                                        <th style="text-align: right;">Overs</th>
                                        <th style="text-align: right;">Mdns</th>
                                        <th style="text-align: right;">Runs</th>
                                        <th style="text-align: right;">Wkts</th>
                                        <th style="text-align: right;">Wd</th>
                                        <th style="text-align: right;">Nb</th>
                                        <th style="text-align: right;">Dots</th>
                                        <th style="text-align: right;">Econ</th>
                                    </tr>
                                </thead>
                                <tbody>
                `;

                inn.bowling.forEach(bowl => {
                    html += `
                        <tr>
                            <td><strong>${bowl.player_name}</strong></td>
                            <td class="val">${bowl.overs}</td>
                            <td class="val">${bowl.maidens}</td>
                            <td class="val">${bowl.runs}</td>
                            <td class="val" style="color:var(--primary);">${bowl.wickets}</td>
                            <td class="val">${bowl.wides}</td>
                            <td class="val">${bowl.no_balls}</td>
                            <td class="val">${bowl.dots}</td>
                            <td class="val">${bowl.econ ? bowl.econ.toFixed(2) : '-'}</td>
                        </tr>
                    `;
                });

                html += `
                                </tbody>
                            </table>
                `;

                // Fall of Wickets
                if (inn.fow && inn.fow.length > 0) {
                    html += `
                            <div class="fow-container" style="margin-top:1rem;">
                                <h4>Fall of Wickets</h4>
                                <div class="fow-list">
                    `;
                    inn.fow.forEach(f => {
                        html += `
                            <span class="fow-item">
                                <strong>${f.wicket_num}-${f.score}</strong> (${f.player_name}, ${f.overs} ov)
                            </span>
                        `;
                    });
                    html += `
                                </div>
                            </div>
                    `;
                }

                html += `
                        </div>
                    </div>
                `;
            });

            // Match notes
            if (data.notes && data.notes.length > 0) {
                html += `
                    <div class="footnotes-container">
                        <h3>Match Footnotes & Milestones</h3>
                        <ul class="footnotes-list">
                `;
                data.notes.forEach(note => {
                    html += `<li>${note}</li>`;
                });
                html += `
                        </ul>
                    </div>
                `;
            }

            body.innerHTML = html;

        } catch (error) {
            console.error("Error fetching match scorecard:", error);
            body.innerHTML = '<div class="error-text">Failed to fetch scorecard.</div>';
        }
    }

    // 5. PLAYERS EXPLORER SEARCH & PROFILES
    const playerInput = document.getElementById("player-search-input");
    let searchTimeout = null;

    if (playerInput) {
        playerInput.addEventListener("input", (e) => {
            clearTimeout(searchTimeout);
            const query = e.target.value.trim();
            
            if (query.length < 2) {
                document.getElementById("player-search-results").innerHTML = '<div class="info-text">Type player name to begin...</div>';
                return;
            }

            searchTimeout = setTimeout(() => {
                performPlayerSearch(query);
            }, 300);
        });
    }

    async function performPlayerSearch(query) {
        const resultsContainer = document.getElementById("player-search-results");
        resultsContainer.innerHTML = '<div class="info-text">Searching...</div>';

        try {
            const res = await fetch(`/api/v1/players/search?query=${encodeURIComponent(query)}`);
            const data = await res.json();
            if (data.error) {
                resultsContainer.innerHTML = '<div class="error-text">Failed to search.</div>';
                return;
            }

            if (data.length === 0) {
                resultsContainer.innerHTML = '<div class="info-text">No players found matching that name.</div>';
                return;
            }

            resultsContainer.innerHTML = "";
            data.forEach(p => {
                const item = document.createElement("div");
                item.className = "player-search-item";
                item.addEventListener("click", () => {
                    document.querySelectorAll(".player-search-item").forEach(i => i.classList.remove("active"));
                    item.classList.add("active");
                    loadPlayerProfile(p.player_id);
                });

                let fmtSummary = "No stats recorded";
                if (p.formats && p.formats.length > 0) {
                    fmtSummary = p.formats.map(f => `${f.format} (${f.runs} runs, ${f.wickets} wkts)`).join(', ');
                }

                item.innerHTML = `
                    <div class="player-name">${p.name}</div>
                    <div class="player-meta">${fmtSummary}</div>
                `;
                resultsContainer.appendChild(item);
            });

        } catch (error) {
            console.error("Error searching players:", error);
            resultsContainer.innerHTML = '<div class="error-text">Error fetching search results.</div>';
        }
    }

    let activePlayerStats = null; // Store stats array to toggle formats

    async function loadPlayerProfile(playerId) {
        document.getElementById("player-profile-placeholder").style.display = "none";
        const profilePanel = document.getElementById("player-profile-panel");
        profilePanel.style.display = "block";

        document.getElementById("player-profile-name").textContent = "Loading Profile...";
        document.getElementById("player-profile-dob").textContent = "";

        try {
            const res = await fetch(`/api/v1/ca/players/${playerId}`);
            const data = await res.json();
            if (data.error) {
                profilePanel.innerHTML = `<div class="error-text">Error: ${data.error}</div>`;
                return;
            }

            document.getElementById("player-profile-name").textContent = data.name;
            document.getElementById("player-profile-dob").textContent = data.dob ? `Born: ${data.dob}` : "DOB: Not Available";

            activePlayerStats = data.stats || [];

            // Trigger default format display (T20)
            const activeTab = document.querySelector(".stats-tab-btn.active");
            const format = activeTab ? activeTab.dataset.format : "T20";
            renderPlayerFormatStats(format);

            // Render Recent Match Appearances
            const recentContainer = document.getElementById("player-recent-matches-container");
            recentContainer.innerHTML = "";

            if (!data.recent_matches || data.recent_matches.length === 0) {
                recentContainer.innerHTML = '<div class="info-text">No recent matches found for this player.</div>';
                return;
            }

            data.recent_matches.forEach(m => {
                const row = document.createElement("div");
                row.className = "recent-match-row";
                row.addEventListener("click", () => showScorecard(m.match_id));
                row.innerHTML = `
                    <div class="left">
                        <span class="title">${m.title}</span>
                        <span class="meta">${m.format} • ${m.date}</span>
                    </div>
                    <span class="result">${m.result}</span>
                `;
                recentContainer.appendChild(row);
            });

        } catch (error) {
            console.error("Error loading player profile:", error);
            profilePanel.innerHTML = '<div class="error-text">Failed to load player details.</div>';
        }
    }

    // Toggle player formats tab click
    const statTabBtns = document.querySelectorAll(".stats-tab-btn");
    statTabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            statTabBtns.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            if (activePlayerStats) {
                renderPlayerFormatStats(btn.dataset.format);
            }
        });
    });

    function renderPlayerFormatStats(format) {
        const stats = activePlayerStats.find(s => s.format === format);

        // Batting elements
        const batFields = ['matches', 'bat_innings', 'bat_runs', 'bat_avg', 'bat_sr', 'highest_score', 'not_outs', 'hundreds', 'fifties', 'fours', 'sixes'];
        batFields.forEach(f => {
            const el = document.getElementById(`p-bat-${f === 'highest_score' ? 'hs' : (f === 'not_outs' ? 'no' : f.replace('bat_', ''))}`);
            if (el) {
                if (stats && stats[f] !== undefined && stats[f] !== null) {
                    let val = stats[f];
                    if (f === 'highest_score' && stats['highest_score_not_out']) {
                        val += "*";
                    }
                    el.textContent = val;
                } else {
                    el.textContent = "-";
                }
            }
        });

        // Bowling elements
        const bowlFields = ['bowl_innings', 'bowl_overs', 'bowl_maidens', 'bowl_runs', 'bowl_wickets', 'bowl_avg', 'bowl_econ', 'bowl_sr', 'five_wickets'];
        bowlFields.forEach(f => {
            const el = document.getElementById(`p-bowl-${f.replace('bowl_', '')}`);
            if (el) {
                if (stats && stats[f] !== undefined && stats[f] !== null) {
                    el.textContent = stats[f];
                } else {
                    el.textContent = "-";
                }
            }
        });

        // Best Bowling Figures (separate rendering)
        const bestEl = document.getElementById("p-bowl-best");
        if (bestEl) {
            if (stats && stats['best_bowling_wickets'] !== null && stats['best_bowling_runs'] !== null) {
                bestEl.textContent = `${stats['best_bowling_wickets']}/${stats['best_bowling_runs']}`;
            } else {
                bestEl.textContent = "-";
            }
        }
    }

    // 6. RECORDS & LEADERBOARDS
    const recCategory = document.getElementById("record-category-select");
    const recFormat = document.getElementById("record-format-select");

    if (recCategory) recCategory.addEventListener("change", loadLeaderboards);
    if (recFormat) recFormat.addEventListener("change", loadLeaderboards);

    async function loadLeaderboards() {
        const category = recCategory.value;
        const format = recFormat.value;

        const table = document.getElementById("records-table");
        table.innerHTML = '<tr><td class="info-text">Loading records list...</td></tr>';
        
        // Update Panel Title
        const selectedOpt = recCategory.options[recCategory.selectedIndex];
        document.getElementById("records-panel-title").textContent = `${selectedOpt.text} (${format})`;

        try {
            const res = await fetch(`/api/v1/records/${category}?format_filter=${format}`);
            const data = await res.json();
            if (data.error) {
                table.innerHTML = `<tr><td class="error-text">Error: ${data.error}</td></tr>`;
                return;
            }

            if (data.length === 0) {
                table.innerHTML = '<tr><td class="info-text">No records found for this category and format.</td></tr>';
                return;
            }

            let html = "";
            if (category === "most_runs") {
                html = `
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Player</th>
                            <th style="text-align: right;">Matches</th>
                            <th style="text-align: right;">Innings</th>
                            <th style="text-align: right;">Runs</th>
                            <th style="text-align: right;">Average</th>
                            <th style="text-align: right;">S-Rate</th>
                            <th style="text-align: right;">Highest Score</th>
                            <th style="text-align: right;">100s</th>
                            <th style="text-align: right;">50s</th>
                        </tr>
                    </thead>
                    <tbody>
                `;
                data.forEach((r, idx) => {
                    html += `
                        <tr style="cursor:pointer;" onclick="showPlayerProfileDirect('${r.player_id}')">
                            <td><strong>#${idx+1}</strong></td>
                            <td><strong style="color:var(--secondary);">${r.player_name}</strong></td>
                            <td class="val">${r.matches}</td>
                            <td class="val">${r.bat_innings}</td>
                            <td class="val" style="color:var(--primary);">${r.bat_runs}</td>
                            <td class="val">${r.bat_avg !== null ? r.bat_avg.toFixed(2) : '-'}</td>
                            <td class="val">${r.bat_sr !== null ? r.bat_sr.toFixed(2) : '-'}</td>
                            <td class="val">${r.highest_score}${r.highest_score_not_out ? '*' : ''}</td>
                            <td class="val">${r.hundreds}</td>
                            <td class="val">${r.fifties}</td>
                        </tr>
                    `;
                });
            } else if (category === "highest_score") {
                html = `
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Player</th>
                            <th style="text-align: right;">Score</th>
                            <th>Dismissal</th>
                            <th>Match</th>
                            <th>Date</th>
                        </tr>
                    </thead>
                    <tbody>
                `;
                data.forEach((r, idx) => {
                    html += `
                        <tr style="cursor:pointer;" onclick="showScorecard('${r.match_id}')">
                            <td><strong>#${idx+1}</strong></td>
                            <td><strong style="color:var(--secondary);">${r.player_name}</strong></td>
                            <td class="val" style="color:var(--primary); font-size:1.1rem;">${r.runs}${r.dismissal_text.includes('not out') ? '*' : ''}</td>
                            <td style="color:var(--text-muted); font-style:italic;">${r.dismissal_text}</td>
                            <td>${r.title}</td>
                            <td>${r.date}</td>
                        </tr>
                    `;
                });
            } else if (category === "most_wickets") {
                html = `
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Player</th>
                            <th style="text-align: right;">Matches</th>
                            <th style="text-align: right;">Innings</th>
                            <th style="text-align: right;">Overs</th>
                            <th style="text-align: right;">Wickets</th>
                            <th style="text-align: right;">Average</th>
                            <th style="text-align: right;">Economy</th>
                            <th style="text-align: right;">S-Rate</th>
                            <th style="text-align: right;">Best Bowling</th>
                            <th style="text-align: right;">5W</th>
                        </tr>
                    </thead>
                    <tbody>
                `;
                data.forEach((r, idx) => {
                    html += `
                        <tr style="cursor:pointer;" onclick="showPlayerProfileDirect('${r.player_id}')">
                            <td><strong>#${idx+1}</strong></td>
                            <td><strong style="color:var(--secondary);">${r.player_name}</strong></td>
                            <td class="val">${r.matches}</td>
                            <td class="val">${r.bowl_innings}</td>
                            <td class="val">${r.bowl_overs}</td>
                            <td class="val" style="color:var(--primary); font-size:1.1rem;">${r.bowl_wickets}</td>
                            <td class="val">${r.bowl_avg !== null ? r.bowl_avg.toFixed(2) : '-'}</td>
                            <td class="val">${r.bowl_econ !== null ? r.bowl_econ.toFixed(2) : '-'}</td>
                            <td class="val">${r.bowl_sr !== null ? r.bowl_sr.toFixed(2) : '-'}</td>
                            <td class="val">${r.best_bowling_wickets !== null ? `${r.best_bowling_wickets}/${r.best_bowling_runs}` : '-'}</td>
                            <td class="val">${r.five_wickets}</td>
                        </tr>
                    `;
                });
            } else if (category === "best_bowling") {
                html = `
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Player</th>
                            <th style="text-align: right;">Figures (W/R)</th>
                            <th style="text-align: right;">Overs</th>
                            <th>Match</th>
                            <th>Date</th>
                        </tr>
                    </thead>
                    <tbody>
                `;
                data.forEach((r, idx) => {
                    html += `
                        <tr style="cursor:pointer;" onclick="showScorecard('${r.match_id}')">
                            <td><strong>#${idx+1}</strong></td>
                            <td><strong style="color:var(--secondary);">${r.player_name}</strong></td>
                            <td class="val" style="color:var(--primary); font-size:1.1rem;">${r.wickets}/${r.runs}</td>
                            <td class="val">${r.overs}</td>
                            <td>${r.title}</td>
                            <td>${r.date}</td>
                        </tr>
                    `;
                });
            } else if (category === "highest_totals") {
                html = `
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Team</th>
                            <th style="text-align: right;">Total</th>
                            <th style="text-align: right;">Overs</th>
                            <th>Opponent / Match</th>
                            <th>Date</th>
                        </tr>
                    </thead>
                    <tbody>
                `;
                data.forEach((r, idx) => {
                    html += `
                        <tr style="cursor:pointer;" onclick="showScorecard('${r.match_id}')">
                            <td><strong>#${idx+1}</strong></td>
                            <td><strong style="color:var(--secondary);">${r.batting_team_name}</strong></td>
                            <td class="val" style="color:var(--primary); font-size:1.1rem;">${r.runs}/${r.wickets}</td>
                            <td class="val">${r.overs}</td>
                            <td>${r.title}</td>
                            <td>${r.date}</td>
                        </tr>
                    `;
                });
            }
            html += "</tbody>";
            table.innerHTML = html;

        } catch (error) {
            console.error("Error loading records:", error);
            table.innerHTML = '<tr><td class="error-text">Failed to fetch leaderboard.</td></tr>';
        }
    }

    // Helper function to switch to player profile tab from other lists (records/matches)
    window.showPlayerProfileDirect = function(playerId) {
        navBtns.forEach(b => b.classList.remove("active"));
        views.forEach(v => v.style.display = "none");

        const btn = document.querySelector('button[data-target="players"]');
        btn.classList.add("active");
        
        const pView = document.getElementById("players-view");
        pView.style.display = "flex";
        
        loadPlayerProfile(playerId);
    }
    
    // Explicit global exposure for onClick bindings in templates
    window.showScorecard = showScorecard;


    // ==========================================
    // Original Simulation Logic
    // ==========================================
    const startBtn = document.getElementById("start-sim-btn");
    let ws = null;

    if (startBtn) {
        startBtn.addEventListener("click", () => {
            const t1 = document.getElementById("team1-select").value;
            const t2 = document.getElementById("team2-select").value;
            const format = document.getElementById("format-select").value;
            
            const commBox = document.getElementById("commentary-box");
            commBox.innerHTML = '<div class="commentary-item system">Connecting to AI Engine...</div>';

            if (ws) {
                ws.close();
            }

            // Detect websocket protocol
            const wsProto = window.location.protocol === "https:" ? "wss:" : "ws:";
            ws = new WebSocket(`${wsProto}//${window.location.host}/ws/simulate`);
            
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
    }
});
