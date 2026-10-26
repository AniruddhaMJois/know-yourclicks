/**
 * KnowYourClicks - Frontend Controller
 * Manages Stats, Shortcuts, Typing Screen with Space Expansion, and Timed Speed Tests.
 */

document.addEventListener('DOMContentLoaded', () => {
    // --- State ---
    let currentTimeframe = '1h';
    let selectedDuration = 30;
    let selectedMode = 'given_text';
    let shortcutsList = [];
    let speedTestInterval = null;
    let speedTestSecondsLeft = 30;
    let speedTestRunning = false;
    let givenPrompt = '';
    let testStartTime = 0;

    // --- DOM Elements ---
    const navTabs = document.querySelectorAll('.nav-tab');
    const tabPanes = document.querySelectorAll('.tab-pane');
    const timeframeBtns = document.querySelectorAll('.btn-timeframe');
    const timerBtns = document.querySelectorAll('.btn-timer');
    const modeRadios = document.querySelectorAll('input[name="speed-mode"]');
    
    // Stats Elements
    const statTotalKeys = document.getElementById('stat-total-keys');
    const statSpaces = document.getElementById('stat-spaces');
    const statSpacesPercent = document.getElementById('stat-spaces-percent');
    const statEdits = document.getElementById('stat-edits');
    const statCorrectionRate = document.getElementById('stat-correction-rate');
    const statPunctuations = document.getElementById('stat-punctuations');
    const chartContainer = document.getElementById('timeline-chart-container');
    const keyDistList = document.getElementById('key-distribution-list');
    const chartTimeframeTag = document.getElementById('chart-timeframe-tag');

    // Typing Screen Elements
    const typingArea = document.getElementById('typing-area');
    const typeWordCount = document.getElementById('type-word-count');
    const typeCharCount = document.getElementById('type-char-count');
    const typeSpaceCount = document.getElementById('type-space-count');
    const btnClearTyping = document.getElementById('btn-clear-typing');
    const expansionAlert = document.getElementById('expansion-alert');
    const alertTrigger = document.getElementById('alert-trigger');
    const alertReplacement = document.getElementById('alert-replacement');
    const shortcutsCheatSheet = document.getElementById('shortcuts-cheat-sheet');

    // Speed Test Elements
    const speedCountdown = document.getElementById('speed-countdown');
    const btnSpeedToggle = document.getElementById('btn-speed-toggle');
    const givenTextArena = document.getElementById('given-text-arena');
    const backgroundArena = document.getElementById('background-arena');
    const testPromptText = document.getElementById('test-prompt-text');
    const testInputArea = document.getElementById('test-input-area');
    const liveWpm = document.getElementById('live-wpm');
    const liveAccuracy = document.getElementById('live-accuracy');
    const liveKeys = document.getElementById('live-keys');
    const bgProgressFill = document.getElementById('bg-progress-fill');
    const speedHistoryTbody = document.getElementById('speed-history-tbody');

    // Shortcut Manager Elements
    const formAddShortcut = document.getElementById('form-add-shortcut');
    const inputShortcut = document.getElementById('input-shortcut');
    const inputReplacement = document.getElementById('input-replacement');
    const shortcutsTableTbody = document.getElementById('shortcuts-table-tbody');

    // System Status
    const systemStatusBox = document.getElementById('system-status-box');

    // Modal
    const modalResult = document.getElementById('modal-result');
    const btnCloseModal = document.getElementById('btn-close-modal');
    const resultWpm = document.getElementById('result-wpm');
    const resultAccuracy = document.getElementById('result-accuracy');
    const resultDuration = document.getElementById('result-duration');
    const resultSpaces = document.getElementById('result-spaces');
    const resultEdits = document.getElementById('result-edits');

    // --- Tab Navigation ---
    navTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            navTabs.forEach(t => t.classList.remove('active'));
            tabPanes.forEach(p => p.classList.remove('active'));
            tab.classList.add('active');
            const target = document.getElementById(tab.dataset.tab);
            if (target) target.classList.add('active');

            if (tab.dataset.tab === 'tab-stats') loadStats();
            if (tab.dataset.tab === 'tab-shortcuts') loadShortcuts();
            if (tab.dataset.tab === 'tab-system') loadSystemStatus();
        });
    });

    // --- Statistics Module ---
    timeframeBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            timeframeBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentTimeframe = btn.dataset.timeframe;
            chartTimeframeTag.textContent = {
                '1h': 'Last 60 Minutes',
                '1d': 'Last 24 Hours',
                '1w': 'Last 7 Days',
                '1m': 'Last 30 Days',
                'all': 'All-Time Record'
            }[currentTimeframe];
            loadStats();
        });
    });

    async function loadStats() {
        try {
            const res = await fetch(`/api/stats?timeframe=${currentTimeframe}`);
            const json = await res.json();
            if (json.success) {
                renderStats(json.data);
            }
        } catch (err) {
            console.error('Error fetching statistics:', err);
        }
    }

    function renderStats(data) {
        statTotalKeys.textContent = data.total_keys.toLocaleString();
        statSpaces.textContent = data.spaces.toLocaleString();
        
        const spacePct = data.total_keys > 0 ? Math.round((data.spaces / data.total_keys) * 100) : 0;
        statSpacesPercent.textContent = `${spacePct}% of total`;

        statEdits.textContent = data.edits.toLocaleString();
        statCorrectionRate.textContent = `${data.correction_rate}% correction rate`;

        statPunctuations.textContent = data.punctuations.toLocaleString();

        renderTimelineChart(data.timeline);
        renderKeyDistribution(data.key_counts, data.total_keys);
    }

    function renderTimelineChart(timeline) {
        if (!timeline || timeline.length === 0) {
            chartContainer.innerHTML = '<div class="empty-state">No keystrokes recorded yet in this timeframe. Start typing!</div>';
            return;
        }

        const maxTotal = Math.max(...timeline.map(t => t.total), 5);
        const height = 200;
        const width = chartContainer.clientWidth || 800;
        const barWidth = Math.max(12, Math.floor((width - 40) / timeline.length) - 6);

        let svgHtml = `<svg width="100%" height="${height}" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">`;
        
        // Grid lines
        for (let i = 0; i <= 4; i++) {
            const y = height - 30 - (i * (height - 50) / 4);
            svgHtml += `<line x1="40" y1="${y}" x2="${width - 10}" y2="${y}" stroke="#334155" stroke-dasharray="3,3" />`;
            const labelVal = Math.round((maxTotal / 4) * i);
            svgHtml += `<text x="30" y="${y + 4}" fill="#64748b" font-size="10" text-anchor="end">${labelVal}</text>`;
        }

        // Bars
        timeline.forEach((pt, idx) => {
            const x = 50 + idx * (barWidth + 6);
            const barH = ((pt.total / maxTotal) * (height - 60));
            const y = height - 30 - barH;
            
            // Sub-bars: Spaces (blue), Edits (red), Punctuation (green)
            const spaceH = (pt.space_count / maxTotal) * (height - 60);
            const editH = (pt.edit_count / maxTotal) * (height - 60);
            const punctH = (pt.punct_count / maxTotal) * (height - 60);

            svgHtml += `
                <g class="chart-bar-group">
                    <rect x="${x}" y="${y}" width="${barWidth}" height="${barH}" fill="#38bdf8" rx="3">
                        <title>${pt.period}: ${pt.total} keys (Spaces: ${pt.space_count}, BS: ${pt.edit_count}, Punct: ${pt.punct_count})</title>
                    </rect>
                    <text x="${x + barWidth / 2}" y="${height - 12}" fill="#64748b" font-size="9" text-anchor="middle">
                        ${pt.period.split(' ').pop().substring(0, 5)}
                    </text>
                </g>
            `;
        });

        svgHtml += `</svg>`;
        chartContainer.innerHTML = svgHtml;
    }

    function renderKeyDistribution(keyCounts, total) {
        if (!keyCounts || keyCounts.length === 0) {
            keyDistList.innerHTML = '<div class="empty-state">No key distribution data available.</div>';
            return;
        }

        const maxKey = keyCounts[0].total || 1;
        keyDistList.innerHTML = keyCounts.map(k => {
            const pct = Math.round((k.total / maxKey) * 100);
            return `
                <div class="dist-row">
                    <div class="dist-name">${escapeHtml(k.key_name)}</div>
                    <div class="dist-bar-bg">
                        <div class="dist-bar-fill" style="width: ${pct}%;"></div>
                    </div>
                    <div class="dist-count">${k.total}</div>
                </div>
            `;
        }).join('');
    }

    // --- Typing Screen & Space Trigger Expander ---
    typingArea.addEventListener('keydown', async (e) => {
        // Enforce privacy key dispatch
        if (e.key === ' ' || e.key === 'Backspace' || e.key === 'Delete' || e.key.length === 1 && !e.key.match(/[a-zA-Z0-9]/)) {
            dispatchKey(e.key, e.key === ' ' ? 'Space' : e.key);
        }

        // TRIGGER ON SPACE: Text expansion
        if (e.key === ' ') {
            const currentVal = typingArea.value;
            const cursorPos = typingArea.selectionStart;
            
            // Check word immediately before cursor
            const textUpToCursor = currentVal.substring(0, cursorPos);
            const wordMatch = textUpToCursor.match(/([a-zA-Z0-9_-]+)$/);
            
            if (wordMatch) {
                const shortcutToken = wordMatch[1].toLowerCase();
                const matched = shortcutsList.find(s => s.shortcut.toLowerCase() === shortcutToken);
                
                if (matched) {
                    e.preventDefault(); // Prevent standard space, we insert expansion + space
                    const wordStart = cursorPos - wordMatch[1].length;
                    const before = currentVal.substring(0, wordStart);
                    const after = currentVal.substring(cursorPos);
                    
                    const replacement = matched.replacement;
                    typingArea.value = before + replacement + ' ' + after;
                    
                    // Set cursor right after expanded text
                    const newCursorPos = wordStart + replacement.length + 1;
                    typingArea.setSelectionRange(newCursorPos, newCursorPos);

                    // Flash notification
                    showExpansionAlert(matched.shortcut, replacement);
                    updateTypingCounters();
                    return;
                }
            }
        }

        setTimeout(updateTypingCounters, 10);
    });

    typingArea.addEventListener('input', updateTypingCounters);

    function updateTypingCounters() {
        const val = typingArea.value;
        const words = val.trim() ? val.trim().split(/\s+/).length : 0;
        typeWordCount.textContent = words;
        typeCharCount.textContent = val.length;
        typeSpaceCount.textContent = (val.match(/ /g) || []).length;
    }

    btnClearTyping.addEventListener('click', () => {
        typingArea.value = '';
        updateTypingCounters();
        typingArea.focus();
    });

    function showExpansionAlert(trigger, replacement) {
        alertTrigger.textContent = trigger;
        alertReplacement.textContent = replacement;
        expansionAlert.style.display = 'block';
        clearTimeout(expansionAlert._timeout);
        expansionAlert._timeout = setTimeout(() => {
            expansionAlert.style.display = 'none';
        }, 3000);
    }

    async function dispatchKey(charVal, keyName) {
        try {
            await fetch('/api/key', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ key: keyName, char: charVal })
            });
        } catch (e) {
            // Background daemon handles direct hardware listener
        }
    }

    // --- Shortcuts Module ---
    async function loadShortcuts() {
        try {
            const res = await fetch('/api/shortcuts');
            const json = await res.json();
            if (json.success) {
                shortcutsList = json.data;
                renderShortcutsTable(shortcutsList);
                renderCheatSheet(shortcutsList);
            }
        } catch (err) {
            console.error('Error fetching shortcuts:', err);
        }
    }

    function renderCheatSheet(list) {
        shortcutsCheatSheet.innerHTML = list.map(s => `
            <div class="cheat-item">
                <span class="cheat-trigger">${escapeHtml(s.shortcut)}</span>
                <span class="cheat-arrow">➔</span>
                <span class="cheat-rep">${escapeHtml(s.replacement)}</span>
            </div>
        `).join('');
    }

    function renderShortcutsTable(list) {
        shortcutsTableTbody.innerHTML = list.map(s => `
            <tr>
                <td><strong class="cheat-trigger">${escapeHtml(s.shortcut)}</strong></td>
                <td>${escapeHtml(s.replacement)}</td>
                <td>${new Date(s.created_at).toLocaleDateString()}</td>
                <td>
                    <button class="btn btn-danger btn-sm" onclick="window.deleteShortcut(${s.id})">Delete</button>
                </td>
            </tr>
        `).join('');
    }

    formAddShortcut.addEventListener('submit', async (e) => {
        e.preventDefault();
        const sc = inputShortcut.value.trim();
        const rep = inputReplacement.value.trim();
        if (!sc || !rep) return;

        try {
            const res = await fetch('/api/shortcuts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ shortcut: sc, replacement: rep })
            });
            const json = await res.json();
            if (json.success) {
                inputShortcut.value = '';
                inputReplacement.value = '';
                loadShortcuts();
            }
        } catch (err) {
            alert('Failed to save shortcut.');
        }
    });

    window.deleteShortcut = async function(id) {
        if (!confirm('Are you sure you want to delete this shortcut?')) return;
        try {
            const res = await fetch(`/api/shortcuts/${id}`, { method: 'DELETE' });
            const json = await res.json();
            if (json.success) loadShortcuts();
        } catch (err) {
            alert('Failed to delete shortcut.');
        }
    };

    // --- Timed Speed Test Module ---
    timerBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            if (speedTestRunning) return;
            timerBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            selectedDuration = parseInt(btn.dataset.duration);
            speedTestSecondsLeft = selectedDuration;
            updateCountdownDisplay(speedTestSecondsLeft);
        });
    });

    modeRadios.forEach(radio => {
        radio.addEventListener('change', () => {
            if (speedTestRunning) return;
            selectedMode = radio.value;
        });
    });

    btnSpeedToggle.addEventListener('click', () => {
        if (speedTestRunning) {
            cancelSpeedTest();
        } else {
            startSpeedTest();
        }
    });

    async function startSpeedTest() {
        speedTestRunning = true;
        speedTestSecondsLeft = selectedDuration;
        btnSpeedToggle.textContent = 'Cancel Speed Test';
        btnSpeedToggle.classList.remove('btn-primary');
        btnSpeedToggle.classList.add('btn-secondary');

        if (selectedMode === 'given_text') {
            givenTextArena.classList.remove('hidden');
            backgroundArena.classList.add('hidden');
            testInputArea.disabled = false;
            testInputArea.value = '';

            // Fetch prompt
            try {
                const res = await fetch('/api/speed/prompts');
                const json = await res.json();
                const prompts = json.data;
                givenPrompt = prompts[Math.floor(Math.random() * prompts.length)];
                testPromptText.textContent = givenPrompt;
            } catch (e) {
                givenPrompt = "The quick brown fox jumps over the lazy dog.";
                testPromptText.textContent = givenPrompt;
            }

            testStartTime = Date.now();
            testInputArea.focus();

            speedTestInterval = setInterval(() => {
                speedTestSecondsLeft--;
                updateCountdownDisplay(speedTestSecondsLeft);
                calculateLiveGivenStats();

                if (speedTestSecondsLeft <= 0) {
                    finishGivenTextTest();
                }
            }, 1000);
        } else {
            // Background passive mode
            backgroundArena.classList.remove('hidden');
            givenTextArena.classList.add('hidden');
            bgProgressFill.style.width = '0%';

            // Notify backend daemon
            await fetch('/api/speed/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mode: 'background', duration: selectedDuration })
            });

            const total = selectedDuration;
            speedTestInterval = setInterval(async () => {
                speedTestSecondsLeft--;
                updateCountdownDisplay(speedTestSecondsLeft);

                const progress = Math.min(100, Math.round(((total - speedTestSecondsLeft) / total) * 100));
                bgProgressFill.style.width = `${progress}%`;

                if (speedTestSecondsLeft <= 0) {
                    clearInterval(speedTestInterval);
                    finishBackgroundTest();
                }
            }, 1000);
        }
    }

    testInputArea.addEventListener('input', () => {
        calculateLiveGivenStats();
        // If user typed the entire prompt before timer ends:
        if (testInputArea.value.length >= givenPrompt.length) {
            finishGivenTextTest();
        }
    });

    function calculateLiveGivenStats() {
        const typed = testInputArea.value;
        const elapsedSec = Math.max(1, (Date.now() - testStartTime) / 1000);
        const elapsedMin = elapsedSec / 60.0;
        
        const grossWpm = Math.round((typed.length / 5.0) / elapsedMin);
        liveWpm.textContent = grossWpm;
        liveKeys.textContent = typed.length;

        // Accuracy
        let matches = 0;
        for (let i = 0; i < typed.length; i++) {
            if (typed[i] === givenPrompt[i]) matches++;
        }
        const acc = typed.length > 0 ? Math.round((matches / typed.length) * 100) : 100;
        liveAccuracy.textContent = `${acc}%`;
    }

    async function finishGivenTextTest() {
        clearInterval(speedTestInterval);
        speedTestRunning = false;
        testInputArea.disabled = true;
        btnSpeedToggle.textContent = 'Start Speed Test';
        btnSpeedToggle.classList.add('btn-primary');
        btnSpeedToggle.classList.remove('btn-secondary');

        const elapsed = Math.max(1, (Date.now() - testStartTime) / 1000);
        const typed = testInputArea.value;

        try {
            const res = await fetch('/api/speed/finish', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt: givenPrompt, typed: typed, elapsed: elapsed })
            });
            const json = await res.json();
            if (json.success) {
                showCompletionModal(json.data);
            }
        } catch (e) {
            console.error('Error submitting test:', e);
        }

        loadSpeedHistory();
        loadStats();
    }

    async function finishBackgroundTest() {
        speedTestRunning = false;
        btnSpeedToggle.textContent = 'Start Speed Test';
        btnSpeedToggle.classList.add('btn-primary');
        btnSpeedToggle.classList.remove('btn-secondary');

        try {
            const res = await fetch('/api/speed/status');
            const json = await res.json();
            if (json.success && json.data.session && json.data.session.result) {
                showCompletionModal(json.data.session.result);
            }
        } catch (e) {
            console.error('Error fetching bg test result:', e);
        }

        loadSpeedHistory();
        loadStats();
    }

    async function cancelSpeedTest() {
        clearInterval(speedTestInterval);
        speedTestRunning = false;
        speedTestSecondsLeft = selectedDuration;
        updateCountdownDisplay(speedTestSecondsLeft);
        btnSpeedToggle.textContent = 'Start Speed Test';
        btnSpeedToggle.classList.add('btn-primary');
        btnSpeedToggle.classList.remove('btn-secondary');
        givenTextArena.classList.add('hidden');
        backgroundArena.classList.add('hidden');

        try {
            await fetch('/api/speed/stop', { method: 'POST' });
        } catch (e) {}
    }

    function updateCountdownDisplay(sec) {
        const m = Math.floor(sec / 60).toString().padStart(2, '0');
        const s = (sec % 60).toString().padStart(2, '0');
        speedCountdown.textContent = `${m}:${s}`;
    }

    function showCompletionModal(result) {
        resultWpm.textContent = result.wpm;
        resultAccuracy.textContent = result.accuracy !== null ? `${result.accuracy}%` : 'N/A (Background)';
        resultDuration.textContent = `${result.duration}s`;
        resultSpaces.textContent = result.spaces;
        resultEdits.textContent = result.backspaces;
        modalResult.classList.remove('hidden');
    }

    btnCloseModal.addEventListener('click', () => {
        modalResult.classList.add('hidden');
    });

    async function loadSpeedHistory() {
        try {
            const res = await fetch('/api/speed/history');
            const json = await res.json();
            if (json.success) {
                renderSpeedHistory(json.data);
            }
        } catch (e) {
            console.error('Error fetching speed history:', e);
        }
    }

    function renderSpeedHistory(list) {
        if (!list || list.length === 0) {
            speedHistoryTbody.innerHTML = '<tr><td colspan="7" class="empty-state">No speed tests completed yet.</td></tr>';
            return;
        }

        speedHistoryTbody.innerHTML = list.map(item => `
            <tr>
                <td>${new Date(item.timestamp).toLocaleString()}</td>
                <td><span class="card-tag">${item.mode === 'given_text' ? 'Given Text' : 'Background'}</span></td>
                <td>${item.duration_seconds}s</td>
                <td><strong class="highlight-blue">${item.wpm}</strong></td>
                <td>${item.cpm}</td>
                <td>${item.accuracy !== null ? item.accuracy + '%' : '--'}</td>
                <td>${item.total_allowed_keys}</td>
            </tr>
        `).join('');
    }

    // --- System Status Module ---
    async function loadSystemStatus() {
        try {
            const res = await fetch('/api/system/status');
            const json = await res.json();
            if (json.success) {
                const info = json.data;
                const lis = info.listener;
                systemStatusBox.innerHTML = `
                    <div style="line-height: 1.8;">
                        <p><strong>Daemon Process:</strong> <span class="highlight-green">RUNNING</span></p>
                        <p><strong>Hardware Listener:</strong> ${lis.active ? '<span class="highlight-green">ACTIVE</span>' : '<span class="highlight-red">WAITING FOR PERMISSIONS</span>'}</p>
                        <p><strong>Device Status:</strong> ${escapeHtml(lis.message)}</p>
                        <p><strong>Monitored Event Devices:</strong> ${lis.monitored_devices.length ? lis.monitored_devices.join(', ') : 'None'}</p>
                    </div>
                `;
            }
        } catch (e) {
            systemStatusBox.innerHTML = '<span class="highlight-red">Could not connect to daemon.</span>';
        }
    }

    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    // --- Periodic Auto-Refresh ---
    setInterval(() => {
        // Refresh active tab data every 6 seconds
        const activeTab = document.querySelector('.nav-tab.active');
        if (activeTab && activeTab.dataset.tab === 'tab-stats') {
            loadStats();
        }
    }, 6000);

    // Initial load
    loadStats();
    loadShortcuts();
    loadSpeedHistory();
    loadSystemStatus();
});
