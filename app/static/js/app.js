class Forwardog {
    constructor() {
        this.currentView = 'metrics-api';
        this.presets = { metrics: {}, logs: {} };
        this.history = this.loadHistoryFromStorage();
        this.maxHistoryItems = 100;
        
        this.init();
    }
    
    
    loadHistoryFromStorage() {
        try {
            const stored = localStorage.getItem('forwardog_history');
            return stored ? JSON.parse(stored) : [];
        } catch (e) {
            console.error('Failed to load history:', e);
            return [];
        }
    }
    
    saveHistoryToStorage() {
        try {
            localStorage.setItem('forwardog_history', JSON.stringify(this.history));
        } catch (e) {
            console.error('Failed to save history:', e);
        }
    }
    
    addToHistory(type, request, result) {
        const entry = {
            id: Date.now().toString(36) + Math.random().toString(36).substr(2, 5),
            type,
            timestamp: new Date().toISOString(),
            request,
            result: {
                success: result.success,
                warning: result.warning || false,
                message: result.warning ? (result.warning_message || result.message) : result.message,
                status_code: result.status_code,
                latency_ms: result.latency_ms
            }
        };
        
        this.history.unshift(entry);
        
        if (this.history.length > this.maxHistoryItems) {
            this.history = this.history.slice(0, this.maxHistoryItems);
        }
        
        this.saveHistoryToStorage();
        this.updateHistoryView();
        this.updateHistoryCount();
    }
    
    updateHistoryCount() {
        const countEl = document.getElementById('history-count');
        if (countEl) {
            countEl.textContent = `${this.history.length} items`;
        }
    }
    
    updateHistoryView() {
        const container = document.getElementById('history-container');
        if (!container) return;
        
        if (this.history.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📜</div>
                    <div class="empty-state-text">History will appear here as you make requests.<br><small>Stored in browser localStorage</small></div>
                </div>
            `;
            return;
        }
        
        container.innerHTML = this.history.map(entry => {
            const date = new Date(entry.timestamp);
            const timeStr = date.toLocaleTimeString();
            const dateStr = date.toLocaleDateString();
            const typeLabels = {
                'metrics-api': 'Metrics API',
                'metrics-form': 'Metrics Form',
                'dogstatsd': 'DogStatsD',
                'logs-api': 'Logs API',
                'logs-form': 'Logs Form',
                'agent-file': 'Agent File'
            };
            
            const statusClass = entry.result.warning ? 'warning' : (entry.result.success ? 'success' : 'error');
            const statusIcon = entry.result.warning ? '⚠️' : (entry.result.success ? '✅' : '❌');
            
            return `
                <div class="history-item ${statusClass}" onclick="forwardog.replayHistory('${entry.id}')">
                    <div class="history-item-header">
                        <span class="history-item-type">${typeLabels[entry.type] || entry.type}</span>
                        <span class="history-item-time">${dateStr} ${timeStr}</span>
                    </div>
                    <div class="history-item-status">
                        <span>${statusIcon}</span>
                        <span>${entry.result.message}</span>
                        ${entry.result.latency_ms ? `<span class="history-item-latency">${entry.result.latency_ms.toFixed(0)}ms</span>` : ''}
                    </div>
                </div>
            `;
        }).join('');
    }
    
    replayHistory(id) {
        const entry = this.history.find(e => e.id === id);
        if (!entry) return;
        
        switch (entry.type) {
            case 'metrics-api':
                this.showView('metrics-api');
                if (typeof entry.request.payload === 'string') {
                    document.getElementById('metrics-api-json').value = entry.request.payload;
                } else {
                    document.getElementById('metrics-api-json').value = JSON.stringify(entry.request.payload, null, 2);
                }
                break;
            case 'metrics-form':
                this.showView('metrics-api');
                switchTab('metrics-api-tabs', 'form');
                if (entry.request.payload && entry.request.payload.series && entry.request.payload.series[0]) {
                    const series = entry.request.payload.series[0];
                    document.getElementById('metric-name').value = series.metric || '';
                    document.getElementById('metric-type').value = series.type || 3;
                    if (series.points && series.points[0]) {
                        document.getElementById('metric-value').value = series.points[0].value || '';
                        document.getElementById('metric-timestamp').value = series.points[0].timestamp || '';
                    }
                    if (series.resources && series.resources[0]) {
                        document.getElementById('metric-host').value = series.resources[0].name || 'forwardog';
                    }
                    document.getElementById('metric-tags').value = (series.tags || []).join(', ');
                }
                break;
            case 'dogstatsd':
                this.showView('dogstatsd');
                if (entry.request.code) {
                    document.getElementById('dogstatsd-code').value = entry.request.code;
                    this.updateCodeHighlight();
                }
                break;
            case 'logs-api':
                this.showView('logs-api');
                if (typeof entry.request.payload === 'string') {
                    document.getElementById('logs-api-json').value = entry.request.payload;
                } else {
                    document.getElementById('logs-api-json').value = JSON.stringify(entry.request.payload, null, 2);
                }
                break;
            case 'logs-form':
                this.showView('logs-api');
                switchTab('logs-api-tabs', 'form');
                if (entry.request.payload && entry.request.payload[0]) {
                    const log = entry.request.payload[0];
                    document.getElementById('log-message').value = log.message || '';
                    document.getElementById('log-service').value = log.service || 'forwardog';
                    document.getElementById('log-source').value = log.ddsource || 'forwardog';
                    document.getElementById('log-status').value = log.status || 'info';
                    document.getElementById('log-tags').value = log.ddtags || '';
                }
                break;
            case 'agent-file':
                this.showView('agent-file');
                if (entry.request.messages) {
                    document.getElementById('agent-file-messages').value = entry.request.messages.join('\n');
                }
                break;
        }
    }
    
    clearHistory() {
        if (confirm('Clear all history? This cannot be undone.')) {
            this.history = [];
            this.saveHistoryToStorage();
            this.updateHistoryView();
            this.updateHistoryCount();
        }
    }
    
    exportHistory() {
        const blob = new Blob([JSON.stringify(this.history, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `forwardog-history-${new Date().toISOString().split('T')[0]}.json`;
        a.click();
        URL.revokeObjectURL(url);
    }
    
    async init() {
        this.validateApiKey();
        
        this.bindNavigation();
        this.bindKeyboardShortcuts();
        this.bindFileUpload();
        await this.loadPresets();
        this.updateInitialTimestamps();
        this.initCodeHighlighting();
        this.updateHistoryView();
        this.updateHistoryCount();
        this.showView('metrics-api');
    }
    
    async validateApiKey() {
        const statusDot = document.getElementById('api-key-status');
        if (!statusDot) return;
        
        try {
            const response = await fetch('/api/validate-key');
            const result = await response.json();
            
            statusDot.classList.remove('validating');
            
            if (result.valid) {
                statusDot.classList.add('active');
                statusDot.title = 'API Key is valid';
            } else {
                statusDot.classList.remove('active');
                statusDot.title = result.message || 'Invalid API Key';
            }
        } catch (error) {
            statusDot.classList.remove('validating');
            statusDot.classList.remove('active');
            statusDot.title = `Validation failed: ${error.message}`;
        }
    }
    
    bindFileUpload() {
        const dropZone = document.getElementById('file-drop-zone');
        if (!dropZone) return;
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            });
        });
        
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.classList.add('drag-over');
            });
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.classList.remove('drag-over');
            });
        });
        
        dropZone.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.processLogFile(files[0]);
            }
        });
    }
    
    handleLogFileUpload(event) {
        const file = event.target.files[0];
        if (file) {
            this.processLogFile(file);
        }
    }
    
    processLogFile(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            const content = e.target.result;
            const textarea = document.getElementById('agent-file-messages');
            
            if (textarea) {
                if (textarea.value.trim()) {
                    if (confirm('Append to existing content? (Cancel to replace)')) {
                        textarea.value = textarea.value + '\n' + content;
                    } else {
                        textarea.value = content;
                    }
                } else {
                    textarea.value = content;
                }
            }
        };
        reader.readAsText(file);
    }
    
    initCodeHighlighting() {
        this.updateCodeHighlight();
        
        const textarea = document.getElementById('dogstatsd-code');
        const highlight = document.querySelector('.code-highlight');
        
        if (textarea && highlight) {
            textarea.addEventListener('scroll', () => {
                highlight.scrollTop = textarea.scrollTop;
                highlight.scrollLeft = textarea.scrollLeft;
            });
        }
    }
    
    updateCodeHighlight() {
        const textarea = document.getElementById('dogstatsd-code');
        const highlightCode = document.getElementById('dogstatsd-code-highlight');
        
        if (textarea && highlightCode && typeof hljs !== 'undefined') {
            let code = textarea.value;
            if (code.endsWith('\n')) {
                code += ' ';
            }
            
            const result = hljs.highlight(code, { language: 'python' });
            highlightCode.innerHTML = result.value;
        }
    }
    
    bindKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                
                switch (this.currentView) {
                    case 'metrics-api':
                        const metricsFormTab = document.getElementById('metrics-api-tabs-form');
                        if (metricsFormTab && !metricsFormTab.classList.contains('hidden')) {
                            this.submitMetricsForm();
                        } else {
                            this.submitMetricsApi();
                        }
                        break;
                    case 'dogstatsd':
                        this.runDogStatsDCode();
                        break;
                    case 'logs-api':
                        const logsFormTab = document.getElementById('logs-api-tabs-form');
                        if (logsFormTab && !logsFormTab.classList.contains('hidden')) {
                            this.submitLogsForm();
                        } else {
                            this.submitLogsApi();
                        }
                        break;
                    case 'agent-file':
                        this.submitAgentFile();
                        break;
                }
            }
        });
        
        document.querySelectorAll('.form-input, .form-select').forEach(el => {
            el.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.focusNextInput(el);
                }
            });
        });
    }
    
    focusNextInput(currentElement) {
        const currentView = document.querySelector('.view-content:not(.hidden)');
        if (!currentView) return;
        
        const focusableElements = Array.from(
            currentView.querySelectorAll('.form-input:not([disabled]), .form-select:not([disabled]), .btn-primary')
        );
        
        const currentIndex = focusableElements.indexOf(currentElement);
        if (currentIndex >= 0 && currentIndex < focusableElements.length - 1) {
            focusableElements[currentIndex + 1].focus();
        }
    }
    
    updateInitialTimestamps() {
        const now = Math.floor(Date.now() / 1000);
        
        const metricsJson = document.getElementById('metrics-api-json');
        if (metricsJson) {
            try {
                const payload = JSON.parse(metricsJson.value);
                if (payload.series) {
                    payload.series.forEach(series => {
                        if (series.points) {
                            series.points.forEach(point => {
                                point.timestamp = now;
                            });
                        }
                    });
                }
                metricsJson.value = JSON.stringify(payload, null, 2);
            } catch (e) {
            }
        }
        
        const timestampInput = document.getElementById('metric-timestamp');
        if (timestampInput) {
            timestampInput.value = now;
        }
    }
    
    bindNavigation() {
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', () => {
                const view = item.dataset.view;
                if (view) {
                    this.showView(view);
                }
            });
        });
    }
    
    showView(view) {
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.toggle('active', item.dataset.view === view);
        });
        
        document.querySelectorAll('.view-content').forEach(content => {
            const shouldShow = content.id === `view-${view}`;
            content.classList.toggle('hidden', !shouldShow);
            
            if (shouldShow) {
                content.style.animation = 'none';
                content.offsetHeight;
                content.style.animation = '';
            }
        });
        
        this.currentView = view;
        
        if (view === 'history') {
            this.updateHistoryView();
            this.updateHistoryCount();
        }
    }
    
    async loadPresets() {
        try {
            const [metricsRes, logsRes, dogstatsdRes] = await Promise.all([
                fetch('/api/metrics/presets'),
                fetch('/api/logs/presets'),
                fetch('/api/metrics/dogstatsd/examples')
            ]);
            
            this.presets.metrics = await metricsRes.json();
            this.presets.logs = await logsRes.json();
            this.presets.dogstatsd = await dogstatsdRes.json();
            
            this.populatePresets();
        } catch (error) {
            console.error('Failed to load presets:', error);
        }
    }
    
    populatePresets() {
        const metricsApiMenu = document.getElementById('presets-metrics-api');
        if (metricsApiMenu && this.presets.metrics.api_presets) {
            metricsApiMenu.innerHTML = this.presets.metrics.api_presets.map((preset, idx) => `
                <div class="preset-item" onclick="forwardog.applyPreset('metrics-api', ${idx})">
                    <div class="preset-name">${preset.name}</div>
                    <div class="preset-desc">${preset.description}</div>
                </div>
            `).join('');
        }
        
        const dogstatsdMenu = document.getElementById('presets-dogstatsd');
        if (dogstatsdMenu && this.presets.dogstatsd && this.presets.dogstatsd.examples) {
            dogstatsdMenu.innerHTML = this.presets.dogstatsd.examples.map((example, idx) => `
                <div class="preset-item" onclick="forwardog.applyPreset('dogstatsd', ${idx})">
                    <div class="preset-name">${example.name}</div>
                    <div class="preset-desc">${example.id}</div>
                </div>
            `).join('');
        }
        
        const logsApiMenu = document.getElementById('presets-logs-api');
        if (logsApiMenu && this.presets.logs.api_presets) {
            logsApiMenu.innerHTML = this.presets.logs.api_presets.map((preset, idx) => `
                <div class="preset-item" onclick="forwardog.applyPreset('logs-api', ${idx})">
                    <div class="preset-name">${preset.name}</div>
                    <div class="preset-desc">${preset.description}</div>
                </div>
            `).join('');
        }
        
        const agentFileMenu = document.getElementById('presets-agent-file');
        if (agentFileMenu && this.presets.logs.agent_file_presets) {
            agentFileMenu.innerHTML = this.presets.logs.agent_file_presets.map((preset, idx) => `
                <div class="preset-item" onclick="forwardog.applyPreset('agent-file', ${idx})">
                    <div class="preset-name">${preset.name}</div>
                    <div class="preset-desc">${preset.description}</div>
                </div>
            `).join('');
        }
    }
    
    applyPreset(type, index) {
        const now = Math.floor(Date.now() / 1000);
        
        if (type === 'metrics-api') {
            const preset = this.presets.metrics.api_presets[index];
            const payload = JSON.parse(JSON.stringify(preset.payload));
            if (payload.series) {
                payload.series.forEach(series => {
                    if (series.points) {
                        series.points.forEach(point => {
                            point.timestamp = now;
                        });
                    }
                });
            }
            document.getElementById('metrics-api-json').value = JSON.stringify(payload, null, 2);
        } else if (type === 'dogstatsd') {
            const example = this.presets.dogstatsd.examples[index];
            document.getElementById('dogstatsd-code').value = example.code;
            this.updateCodeHighlight();
            document.getElementById('dogstatsd-output').classList.add('hidden');
        } else if (type === 'logs-api') {
            const preset = this.presets.logs.api_presets[index];
            document.getElementById('logs-api-json').value = JSON.stringify(preset.payload, null, 2);
        } else if (type === 'agent-file') {
            const preset = this.presets.logs.agent_file_presets[index];
            let messages = preset.messages.join('\n');
            
            if (preset.has_timestamp) {
                const nowUnix = Math.floor(Date.now() / 1000);
                const nowIso = new Date().toISOString();
                messages = messages.replace(/NOW_ISO/g, nowIso);
                messages = messages.replace(/NOW/g, nowUnix.toString());
            }
            
            document.getElementById('agent-file-messages').value = messages;
            
            if (preset.service) {
                document.getElementById('agent-file-service').value = preset.service;
            }
        }
        
        document.querySelectorAll('.presets-menu').forEach(menu => {
            menu.classList.remove('open');
        });
    }
    
    togglePresets(menuId) {
        const menu = document.getElementById(menuId);
        if (menu) {
            menu.classList.toggle('open');
        }
    }
    
    async submitMetricsApi() {
        const btn = document.getElementById('btn-submit-metrics-api');
        const jsonInput = document.getElementById('metrics-api-json');
        
        try {
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Sending...';
            
            const payload = JSON.parse(jsonInput.value);
            const timestampWarnings = this.checkMetricsTimestamp(payload);
            
            const response = await fetch('/api/metrics/api/submit-json', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ payload })
            });
            
            const result = await response.json();
            
            if (timestampWarnings.length > 0 && result.success) {
                const warningResult = {
                    ...result,
                    warning: true,
                    message: result.message,
                    warning_message: `Timestamp out of range:\n${timestampWarnings.join('\n')}`
                };
                this.addWarningResult(warningResult);
                this.addToHistory('metrics-api', { payload }, warningResult);
            } else {
                this.addResult(result);
                this.addToHistory('metrics-api', { payload }, result);
            }
            
        } catch (error) {
            const errorResult = {
                success: false,
                message: `Error: ${error.message}`,
                error_hint: 'Check JSON syntax'
            };
            this.addResult(errorResult);
            this.addToHistory('metrics-api', { payload: jsonInput.value }, errorResult);
        } finally {
            btn.disabled = false;
            btn.innerHTML = '📤 Submit Metrics';
        }
    }
    
    setFormTimestampNow() {
        const timestampInput = document.getElementById('metric-timestamp');
        if (timestampInput) {
            timestampInput.value = Math.floor(Date.now() / 1000);
        }
    }
    
    async submitMetricsForm() {
        const btn = document.getElementById('btn-submit-metrics-form');
        
        try {
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Sending...';
            
            const metric = document.getElementById('metric-name').value;
            const type = parseInt(document.getElementById('metric-type').value);
            const value = parseFloat(document.getElementById('metric-value').value);
            const timestampInput = document.getElementById('metric-timestamp').value;
            const timestamp = timestampInput ? parseInt(timestampInput) : Math.floor(Date.now() / 1000);
            const host = document.getElementById('metric-host').value || 'forwardog';
            const tagsInput = document.getElementById('metric-tags').value;
            const tags = tagsInput ? tagsInput.split(',').map(t => t.trim()).filter(t => t) : [];
            
            const payload = {
                series: [{
                    metric,
                    type,
                    points: [{ timestamp, value }],
                    resources: [{ name: host, type: 'host' }],
                    tags
                }]
            };
            
            const timestampWarnings = this.checkMetricsTimestamp(payload);
            
            const response = await fetch('/api/metrics/api/submit-json', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ payload })
            });
            
            const result = await response.json();
            
            if (timestampWarnings.length > 0 && result.success) {
                const warningResult = {
                    ...result,
                    warning: true,
                    message: result.message,
                    warning_message: `Timestamp out of range:\n${timestampWarnings.join('\n')}`
                };
                this.addWarningResult(warningResult);
                this.addToHistory('metrics-form', { payload }, warningResult);
            } else {
                this.addResult(result);
                this.addToHistory('metrics-form', { payload }, result);
            }
            
        } catch (error) {
            const errorResult = {
                success: false,
                message: `Error: ${error.message}`
            };
            this.addResult(errorResult);
            this.addToHistory('metrics-form', {}, errorResult);
        } finally {
            btn.disabled = false;
            btn.innerHTML = '📤 Submit Metric';
        }
    }
    
    async runDogStatsDCode() {
        const btn = document.getElementById('btn-run-dogstatsd');
        const codeInput = document.getElementById('dogstatsd-code');
        const outputDiv = document.getElementById('dogstatsd-output');
        const outputHeader = outputDiv.querySelector('.output-header');
        const outputContent = outputDiv.querySelector('.output-content');
        
        const code = codeInput.value;
        
        try {
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Running...';
            
            const response = await fetch('/api/metrics/dogstatsd/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code })
            });
            
            const result = await response.json();
            
            outputDiv.classList.remove('hidden');
            
            if (result.success) {
                outputHeader.textContent = '📤 Output';
                outputHeader.classList.remove('error');
                outputContent.classList.remove('error');
                outputContent.textContent = result.response_body?.output || '(no output)';
            } else {
                outputHeader.textContent = '❌ Error';
                outputHeader.classList.add('error');
                outputContent.classList.add('error');
                let errorText = result.message;
                if (result.response_body?.traceback) {
                    errorText += '\n\n' + result.response_body.traceback;
                }
                outputContent.textContent = errorText;
            }
            
            this.addResult(result);
            this.addToHistory('dogstatsd', { code }, result);
            
        } catch (error) {
            outputDiv.classList.remove('hidden');
            outputHeader.textContent = '❌ Error';
            outputHeader.classList.add('error');
            outputContent.classList.add('error');
            outputContent.textContent = error.message;
            
            const errorResult = {
                success: false,
                message: `Error: ${error.message}`
            };
            this.addResult(errorResult);
            this.addToHistory('dogstatsd', { code }, errorResult);
        } finally {
            btn.disabled = false;
            btn.innerHTML = '▶️ Run Code';
        }
    }
    
    async submitDogStatsD() {
        const btn = document.getElementById('btn-submit-dogstatsd');
        const lineInput = document.getElementById('dogstatsd-line');
        
        if (!btn || !lineInput) return;
        
        try {
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Sending...';
            
            const response = await fetch('/api/metrics/dogstatsd/submit-raw', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ line: lineInput.value })
            });
            
            const result = await response.json();
            this.addResult(result);
            
        } catch (error) {
            this.addResult({
                success: false,
                message: `Error: ${error.message}`
            });
        } finally {
            btn.disabled = false;
            btn.innerHTML = '📤 Send via DogStatsD';
        }
    }
    
    async submitDogStatsDForm() {
        const btn = document.getElementById('btn-submit-dogstatsd-form');
        
        try {
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Sending...';
            
            const metric = document.getElementById('dogstatsd-metric-name').value;
            const value = parseFloat(document.getElementById('dogstatsd-metric-value').value);
            const metricType = document.getElementById('dogstatsd-metric-type').value;
            const tagsInput = document.getElementById('dogstatsd-metric-tags').value;
            const tags = tagsInput ? tagsInput.split(',').map(t => t.trim()).filter(t => t) : [];
            const sampleRate = parseFloat(document.getElementById('dogstatsd-sample-rate').value) || 1.0;
            
            const response = await fetch('/api/metrics/dogstatsd/submit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    metric,
                    value,
                    metric_type: metricType,
                    tags,
                    sample_rate: sampleRate
                })
            });
            
            const result = await response.json();
            this.addResult(result);
            
        } catch (error) {
            this.addResult({
                success: false,
                message: `Error: ${error.message}`
            });
        } finally {
            btn.disabled = false;
            btn.innerHTML = '📤 Send Metric';
        }
    }
    
    async submitLogsApi() {
        const btn = document.getElementById('btn-submit-logs-api');
        const jsonInput = document.getElementById('logs-api-json');
        
        try {
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Sending...';
            
            const payload = JSON.parse(jsonInput.value);
            const timestampWarnings = this.checkLogsTimestamp(payload);
            
            const response = await fetch('/api/logs/api/submit-json', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ payload })
            });
            
            const result = await response.json();
            
            if (timestampWarnings.length > 0 && result.success) {
                const warningResult = {
                    ...result,
                    warning: true,
                    message: result.message,
                    warning_message: `Timestamp out of range:\n${timestampWarnings.join('\n')}`
                };
                this.addWarningResult(warningResult);
                this.addToHistory('logs-api', { payload }, warningResult);
            } else {
                this.addResult(result);
                this.addToHistory('logs-api', { payload }, result);
            }
            
        } catch (error) {
            const errorResult = {
                success: false,
                message: `Error: ${error.message}`,
                error_hint: 'Check JSON syntax'
            };
            this.addResult(errorResult);
            this.addToHistory('logs-api', { payload: jsonInput.value }, errorResult);
        } finally {
            btn.disabled = false;
            btn.innerHTML = '📤 Submit Logs';
        }
    }
    
    async submitLogsForm() {
        const btn = document.getElementById('btn-submit-logs-form');
        
        try {
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Sending...';
            
            const message = document.getElementById('log-message').value;
            const service = document.getElementById('log-service').value || 'forwardog';
            const source = document.getElementById('log-source').value || 'forwardog';
            const status = document.getElementById('log-status').value;
            const tagsInput = document.getElementById('log-tags').value;
            
            const payload = [{
                message,
                service,
                ddsource: source,
                status
            }];
            
            if (tagsInput) {
                payload[0].ddtags = tagsInput;
            }
            
            const timestampWarnings = this.checkLogsTimestamp(payload);
            
            const response = await fetch('/api/logs/api/submit-json', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ payload })
            });
            
            const result = await response.json();
            
            if (timestampWarnings.length > 0 && result.success) {
                const warningResult = {
                    ...result,
                    warning: true,
                    message: result.message,
                    warning_message: `Timestamp out of range:\n${timestampWarnings.join('\n')}`
                };
                this.addWarningResult(warningResult);
                this.addToHistory('logs-form', { payload }, warningResult);
            } else {
                this.addResult(result);
                this.addToHistory('logs-form', { payload }, result);
            }
            
        } catch (error) {
            const errorResult = {
                success: false,
                message: `Error: ${error.message}`
            };
            this.addResult(errorResult);
            this.addToHistory('logs-form', {}, errorResult);
        } finally {
            btn.disabled = false;
            btn.innerHTML = '📤 Submit Log';
        }
    }
    
    updateAgentFileTimestamps() {
        const textarea = document.getElementById('agent-file-messages');
        if (!textarea) return;
        
        const now = new Date().toISOString();
        const lines = textarea.value.split('\n');
        
        const updatedLines = lines.map(line => {
            const isoPattern = /\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?/g;
            const unixPattern = /"timestamp"\s*:\s*(\d{10,13})/g;
            
            let updated = line.replace(isoPattern, now);
            
            updated = updated.replace(unixPattern, (match, ts) => {
                const nowUnix = ts.length > 10 ? Date.now() : Math.floor(Date.now() / 1000);
                return `"timestamp": ${nowUnix}`;
            });
            
            return updated;
        });
        
        textarea.value = updatedLines.join('\n');
    }
    
    checkTimestampRange(messages) {
        const warnings = [];
        const now = Date.now();
        const maxPastHours = 18;
        const maxFutureHours = 2;
        const minTime = now - (maxPastHours * 60 * 60 * 1000);
        const maxTime = now + (maxFutureHours * 60 * 60 * 1000);
        
        messages.forEach((msg, idx) => {
            const isoMatch = msg.match(/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?/);
            const unixMatch = msg.match(/"timestamp"\s*:\s*(\d{10,13})/);
            
            let timestamp = null;
            
            if (isoMatch) {
                timestamp = new Date(isoMatch[0]).getTime();
            } else if (unixMatch) {
                const ts = parseInt(unixMatch[1]);
                timestamp = ts > 9999999999 ? ts : ts * 1000;
            }
            
            if (timestamp) {
                if (timestamp < minTime) {
                    warnings.push(`Line ${idx + 1}: Timestamp is more than ${maxPastHours} hours in the past`);
                } else if (timestamp > maxTime) {
                    warnings.push(`Line ${idx + 1}: Timestamp is more than ${maxFutureHours} hours in the future`);
                }
            }
        });
        
        return warnings;
    }
    
    checkMetricsTimestamp(payload) {
        const warnings = [];
        const now = Date.now();
        const maxPastHours = 1;
        const maxFutureMinutes = 10;
        const minTime = now - (maxPastHours * 60 * 60 * 1000);
        const maxTime = now + (maxFutureMinutes * 60 * 1000);
        
        if (payload.series) {
            payload.series.forEach((series, seriesIdx) => {
                if (series.points) {
                    series.points.forEach((point, pointIdx) => {
                        if (point.timestamp) {
                            const ts = point.timestamp > 9999999999 ? point.timestamp : point.timestamp * 1000;
                            if (ts < minTime) {
                                warnings.push(`Series ${seriesIdx + 1}, Point ${pointIdx + 1}: Timestamp is more than ${maxPastHours} hour in the past`);
                            } else if (ts > maxTime) {
                                warnings.push(`Series ${seriesIdx + 1}, Point ${pointIdx + 1}: Timestamp is more than ${maxFutureMinutes} minutes in the future`);
                            }
                        }
                    });
                }
            });
        }
        
        return warnings;
    }
    
    checkLogsTimestamp(payload) {
        const warnings = [];
        const now = Date.now();
        const maxPastHours = 18;
        const maxFutureHours = 2;
        const minTime = now - (maxPastHours * 60 * 60 * 1000);
        const maxTime = now + (maxFutureHours * 60 * 60 * 1000);
        
        const logs = Array.isArray(payload) ? payload : [payload];
        
        logs.forEach((log, idx) => {
            const timestamp = log.timestamp || log.date;
            if (timestamp) {
                let ts;
                if (typeof timestamp === 'string') {
                    ts = new Date(timestamp).getTime();
                } else {
                    ts = timestamp > 9999999999 ? timestamp : timestamp * 1000;
                }
                
                if (ts < minTime) {
                    warnings.push(`Log ${idx + 1}: Timestamp is more than ${maxPastHours} hours in the past`);
                } else if (ts > maxTime) {
                    warnings.push(`Log ${idx + 1}: Timestamp is more than ${maxFutureHours} hours in the future`);
                }
            }
        });
        
        return warnings;
    }
    
    async submitAgentFile() {
        const btn = document.getElementById('btn-submit-agent-file');
        const messagesInput = document.getElementById('agent-file-messages');
        
        try {
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Writing...';
            
            const messages = messagesInput.value.split('\n').filter(line => line.trim());
            
            const timestampWarnings = this.checkTimestampRange(messages);
            
            const response = await fetch('/api/logs/agent-file/submit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    messages,
                    format: 'raw',
                    service: document.getElementById('agent-file-service')?.value || 'forwardog',
                    source: document.getElementById('agent-file-source')?.value || 'forwardog'
                })
            });
            
            const result = await response.json();
            
            if (timestampWarnings.length > 0 && result.success) {
                const warningResult = {
                    ...result,
                    warning: true,
                    message: result.message,
                    warning_message: `Timestamp out of range:\n${timestampWarnings.join('\n')}`
                };
                this.addWarningResult(warningResult);
                this.addToHistory('agent-file', { messages }, warningResult);
            } else {
                this.addResult(result);
                this.addToHistory('agent-file', { messages }, result);
            }
            
        } catch (error) {
            const errorResult = {
                success: false,
                message: `Error: ${error.message}`
            };
            this.addResult(errorResult);
            this.addToHistory('agent-file', { messages: messagesInput.value }, errorResult);
        } finally {
            btn.disabled = false;
            btn.innerHTML = '📝 Write to Log File';
        }
    }
    
    addWarningResult(result) {
        const container = document.getElementById('results-container');
        const emptyState = container.querySelector('.empty-state');
        if (emptyState) {
            emptyState.remove();
        }
        
        const resultHtml = `
            <div class="result-card warning">
                <div class="result-header">
                    <div class="result-status">
                        <span class="result-status-icon">⚠️</span>
                        <span class="result-status-text">Warning</span>
                    </div>
                    <div class="result-meta">
                        ${result.status_code ? `<span>HTTP ${result.status_code}</span>` : ''}
                        ${result.latency_ms ? `<span>${result.latency_ms.toFixed(2)}ms</span>` : ''}
                    </div>
                </div>
                <div class="result-details">
                    <div class="result-details-item">
                        <span class="result-details-label">Message</span>
                        <span class="result-details-value">${result.message}</span>
                    </div>
                    ${result.request_id ? `
                    <div class="result-details-item">
                        <span class="result-details-label">Request ID</span>
                        <span class="result-details-value">${result.request_id}</span>
                    </div>
                    ` : ''}
                    ${result.warning_message ? `
                    <div class="result-details-item warning-item">
                        <span class="result-details-value warning-text">${result.warning_message.replace(/\n/g, '<br>')}</span>
                    </div>
                    ` : ''}
                </div>
            </div>
        `;
        
        container.insertAdjacentHTML('afterbegin', resultHtml);
        
        const results = container.querySelectorAll('.result-card');
        if (results.length > 20) {
            for (let i = 20; i < results.length; i++) {
                results[i].remove();
            }
        }
    }
    
    addResult(result) {
        const container = document.getElementById('results-container');
        const emptyState = container.querySelector('.empty-state');
        if (emptyState) {
            emptyState.remove();
        }
        
        const resultHtml = `
            <div class="result-card ${result.success ? 'success' : 'error'}">
                <div class="result-header">
                    <div class="result-status">
                        <span class="result-status-icon">${result.success ? '✅' : '❌'}</span>
                        <span class="result-status-text">${result.success ? 'Success' : 'Failed'}</span>
                    </div>
                    <div class="result-meta">
                        ${result.status_code ? `<span>HTTP ${result.status_code}</span>` : ''}
                        ${result.latency_ms ? `<span>${result.latency_ms.toFixed(2)}ms</span>` : ''}
                    </div>
                </div>
                <div class="result-details">
                    <div class="result-details-item">
                        <span class="result-details-label">Message</span>
                        <span class="result-details-value">${result.message}</span>
                    </div>
                    ${result.request_id ? `
                    <div class="result-details-item">
                        <span class="result-details-label">Request ID</span>
                        <span class="result-details-value">${result.request_id}</span>
                    </div>
                    ` : ''}
                </div>
                ${result.response_body ? `
                <div class="result-body-json">
                    <pre>${typeof result.response_body === 'string' ? result.response_body : JSON.stringify(result.response_body, null, 2)}</pre>
                </div>
                ` : ''}
                ${result.error_hint ? `
                <div class="result-hint">
                    💡 ${result.error_hint}
                </div>
                ` : ''}
            </div>
        `;
        
        container.insertAdjacentHTML('afterbegin', resultHtml);
        
        const results = container.querySelectorAll('.result-card');
        if (results.length > 20) {
            results[results.length - 1].remove();
        }
    }
    
    clearResults() {
        document.getElementById('results-container').innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📋</div>
                <div class="empty-state-text">No results yet. Submit a request to see results here.</div>
            </div>
        `;
    }
    
    insertNowTimestamp(inputId) {
        const input = document.getElementById(inputId);
        if (input) {
            const textarea = document.getElementById('metrics-api-json');
            if (textarea) {
                const now = Math.floor(Date.now() / 1000);
                try {
                    const json = JSON.parse(textarea.value);
                    if (json.series) {
                        json.series.forEach(series => {
                            if (series.points) {
                                series.points.forEach(point => {
                                    point.timestamp = now;
                                });
                            }
                        });
                    }
                    textarea.value = JSON.stringify(json, null, 2);
                } catch (e) {
                    alert(`Current timestamp: ${now}`);
                }
            }
        }
    }
    
    generateRandomValue(type = 'gauge') {
        switch (type) {
            case 'gauge':
                return Math.random() * 100;
            case 'count':
                return Math.floor(Math.random() * 1000);
            case 'sine':
                return 50 + 50 * Math.sin(Date.now() / 10000);
            default:
                return Math.random() * 100;
        }
    }
    
    formatJson(textareaId) {
        const textarea = document.getElementById(textareaId);
        if (textarea) {
            try {
                const json = JSON.parse(textarea.value);
                textarea.value = JSON.stringify(json, null, 2);
            } catch (e) {
                alert('Invalid JSON');
            }
        }
    }
    
    minifyJson(textareaId) {
        const textarea = document.getElementById(textareaId);
        if (textarea) {
            try {
                const json = JSON.parse(textarea.value);
                textarea.value = JSON.stringify(json);
            } catch (e) {
                alert('Invalid JSON');
            }
        }
    }
}

function switchTab(containerId, tabId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    container.querySelectorAll('.panel-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabId);
    });
    
    const jsonTab = document.getElementById(`${containerId}-json`);
    const formTab = document.getElementById(`${containerId}-form`);
    
    [jsonTab, formTab].forEach(tab => {
        if (!tab) return;
        const shouldShow = (tab === jsonTab && tabId === 'json') || (tab === formTab && tabId === 'form');
        tab.classList.toggle('hidden', !shouldShow);
        
        if (shouldShow) {
            tab.style.animation = 'none';
            tab.offsetHeight;
            tab.style.animation = '';
        }
    });
}

let forwardog;
document.addEventListener('DOMContentLoaded', () => {
    forwardog = new Forwardog();
});

document.addEventListener('click', (e) => {
    if (!e.target.closest('.presets-dropdown')) {
        document.querySelectorAll('.presets-menu').forEach(menu => {
            menu.classList.remove('open');
        });
    }
});

(function initTheme() {
    const themeToggle = document.getElementById('theme-toggle');
    const html = document.documentElement;
    
    function getSystemTheme() {
        return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
    }
    
    function setTheme(theme) {
        html.setAttribute('data-theme', theme);
        localStorage.setItem('forwardog-theme', theme);
        updateToggleTitle(theme);
    }
    
    function updateToggleTitle(theme) {
        if (themeToggle) {
            themeToggle.title = theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode';
        }
    }
    
    function initializeTheme() {
        const savedTheme = localStorage.getItem('forwardog-theme');
        if (savedTheme) {
            setTheme(savedTheme);
        } else {
            const systemTheme = getSystemTheme();
            html.setAttribute('data-theme', systemTheme);
            updateToggleTitle(systemTheme);
        }
    }
    
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const currentTheme = html.getAttribute('data-theme') || getSystemTheme();
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            setTheme(newTheme);
        });
    }
    
    window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', (e) => {
        if (!localStorage.getItem('forwardog-theme')) {
            const newTheme = e.matches ? 'light' : 'dark';
            html.setAttribute('data-theme', newTheme);
            updateToggleTitle(newTheme);
        }
    });
    
    initializeTheme();
})();

