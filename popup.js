const BACKEND_URL = 'http://127.0.0.1:5601';
let currentAlertType = 'price';

document.addEventListener('DOMContentLoaded', () => {
    fetchPrice();
    fetchAlerts();
    fetchHistory();
    updateStatus('Connected');

    // Tab switching
    document.querySelectorAll('.alert-tab').forEach(tab => {
        tab.addEventListener('click', function() {
            document.querySelectorAll('.alert-tab').forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            currentAlertType = this.dataset.type;
            showForm(currentAlertType);
        });
    });

    // Set Alert
    document.getElementById('setAlertBtn').addEventListener('click', () => {
        let alertData = { type: currentAlertType };
        
        switch(currentAlertType) {
            case 'price':
                const minPrice = document.getElementById('minPrice').value;
                const maxPrice = document.getElementById('maxPrice').value;
                if (minPrice || maxPrice) {
                    alertData.min_price = minPrice ? parseFloat(minPrice) : null;
                    alertData.max_price = maxPrice ? parseFloat(maxPrice) : null;
                } else {
                    alert('Please set at least one threshold (min or max price).');
                    return;
                }
                break;
                
            case 'volume_spike':
                alertData.volume_threshold = parseFloat(document.getElementById('volumeThreshold').value);
                break;
                
            case 'volatility_shift':
                alertData.volatility_threshold = parseFloat(document.getElementById('volatilityThreshold').value);
                break;
                
            case 'rsi':
                alertData.rsi_threshold = parseFloat(document.getElementById('rsiThreshold').value);
                alertData.rsi_direction = document.getElementById('rsiDirection').value;
                break;
                
            case 'golden_cross':
                // No additional params needed
                break;
        }
        
        const btn = document.getElementById('setAlertBtn');
        btn.disabled = true;
        btn.textContent = 'Setting...';

        fetch(`${BACKEND_URL}/api/set_alert`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(alertData)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Alert set:', data);
            fetchAlerts();
            updateStatus('Alert set! ✓', 'success');
            setTimeout(() => updateStatus('Connected'), 2000);
        })
        .catch(error => {
            console.error('Error setting alert:', error);
            updateStatus('Error setting alert', 'error');
            setTimeout(() => updateStatus('Connected'), 2000);
        })
        .finally(() => {
            btn.disabled = false;
            btn.textContent = 'Set Smart Alert';
        });
    });

    // Clear History
    document.getElementById('clearHistoryBtn').addEventListener('click', () => {
        if (!confirm('Clear all notification history?')) return;
        
        chrome.runtime.sendMessage({ action: 'clearHistory' }, (response) => {
            if (response && response.success) {
                fetchHistory();
                updateStatus('History cleared ✓', 'success');
                setTimeout(() => updateStatus('Connected'), 2000);
            }
        });
    });
});

function showForm(type) {
    document.querySelectorAll('.alert-form').forEach(f => f.style.display = 'none');
    const formMap = {
        'price': 'priceForm',
        'volume_spike': 'volumeForm',
        'volatility_shift': 'volatilityForm',
        'rsi': 'rsiForm',
        'golden_cross': 'crossForm'
    };
    const form = document.getElementById(formMap[type]);
    if (form) form.style.display = 'block';
}

function fetchPrice() {
    fetch(`${BACKEND_URL}/api/price`)
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
        .then(data => {
            const display = document.getElementById('priceDisplay');
            if (data.price) {
                display.textContent = `$${data.price.toLocaleString()}`;
                updateStatus('Connected');
            } else {
                display.textContent = 'Error';
                updateStatus('Error fetching price', 'error');
            }
        })
        .catch(error => {
            console.error('Error fetching price:', error);
            document.getElementById('priceDisplay').textContent = '⚠️ Offline';
            updateStatus('Backend offline', 'error');
        });
}

function fetchAlerts() {
    fetch(`${BACKEND_URL}/api/alerts`)
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
        .then(data => {
            const list = document.getElementById('alertsList');
            if (data.alerts && data.alerts.length > 0) {
                list.innerHTML = data.alerts.map(alert => {
                    let description = '';
                    let typeLabel = '';
                    
                    switch(alert.type) {
                        case 'price':
                            const minText = alert.min_price ? `Below $${alert.min_price.toLocaleString()}` : '';
                            const maxText = alert.max_price ? `Above $${alert.max_price.toLocaleString()}` : '';
                            description = [minText, maxText].filter(t => t).join(' OR ');
                            typeLabel = '💰';
                            break;
                        case 'volume_spike':
                            description = `Volume > ${alert.volume_threshold}x Average`;
                            typeLabel = '📊';
                            break;
                        case 'volatility_shift':
                            description = `Volatility > ${(alert.volatility_threshold * 100).toFixed(0)}%`;
                            typeLabel = '⚡';
                            break;
                        case 'rsi':
                            const dir = alert.rsi_direction === 'above' ? '>' : '<';
                            description = `RSI ${dir} ${alert.rsi_threshold}`;
                            typeLabel = '📈';
                            break;
                        case 'golden_cross':
                            description = '50/200 EMA Crossover';
                            typeLabel = '🔀';
                            break;
                        default:
                            description = alert.type;
                            typeLabel = '📌';
                    }
                    
                    const statusClass = alert.triggered ? 'triggered' : 'active';
                    const statusText = alert.triggered ? '⚠️ Triggered' : '● Monitoring';
                    
                    return `
                        <div class="alert-item">
                            <div class="alert-info">
                                <div>
                                    <span class="type-badge">${typeLabel}</span>
                                    <span class="alert-price">${description}</span>
                                </div>
                                <div class="alert-thresholds">ID: #${alert.id}</div>
                            </div>
                            <div style="display:flex;align-items:center;gap:8px;">
                                <span class="alert-status ${statusClass}">${statusText}</span>
                                <button class="btn btn-danger delete-btn" data-id="${alert.id}">✕</button>
                            </div>
                        </div>
                    `;
                }).join('');
                
                document.querySelectorAll('.delete-btn').forEach(button => {
                    button.addEventListener('click', function() {
                        const alertId = parseInt(this.dataset.id);
                        deleteAlert(alertId);
                    });
                });
            } else {
                list.innerHTML = '<div class="no-alerts">No alerts set</div>';
            }
        })
        .catch(error => {
            console.error('Error fetching alerts:', error);
            document.getElementById('alertsList').innerHTML = 
                '<div class="no-alerts" style="color:#ef4444;">⚠️ Could not load alerts</div>';
        });
}

function deleteAlert(alertId) {
    if (!confirm(`Delete alert #${alertId}?`)) return;
    
    fetch(`${BACKEND_URL}/api/delete_alert/${alertId}`, {
        method: 'DELETE'
    })
    .then(response => {
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return response.json();
    })
    .then(data => {
        console.log('Alert deleted:', data);
        fetchAlerts();
        updateStatus('Alert deleted ✓', 'success');
        setTimeout(() => updateStatus('Connected'), 2000);
    })
    .catch(error => {
        console.error('Error deleting alert:', error);
        updateStatus('Error deleting alert', 'error');
        setTimeout(() => updateStatus('Connected'), 2000);
    });
}

function fetchHistory() {
    chrome.runtime.sendMessage({ action: 'getHistory' }, (response) => {
        if (response && response.history) {
            const history = response.history;
            const list = document.getElementById('historyList');
            const badge = document.getElementById('notificationBadge');
            
            const unreadCount = history.filter(h => !h.read).length;
            
            if (unreadCount > 0) {
                badge.style.display = 'inline';
                badge.textContent = `🔔 ${unreadCount}`;
            } else {
                badge.style.display = 'none';
            }
            
            if (history.length > 0) {
                list.innerHTML = history.slice(0, 20).map(item => `
                    <div class="history-item ${item.read ? '' : 'unread'}">
                        <div><strong>${item.title}</strong></div>
                        <div class="msg">${item.message}</div>
                        <div class="time">${item.timestamp} ${item.read ? '✓' : '🔔'}</div>
                    </div>
                `).join('');
            } else {
                list.innerHTML = '<div class="no-alerts">No notifications yet</div>';
            }
        }
    });
}

function updateStatus(message, type = '') {
    const status = document.getElementById('statusDisplay');
    status.textContent = `● ${message}`;
    status.className = 'status ' + type;
}

// Refresh every 30 seconds
setInterval(() => {
    fetchPrice();
    fetchAlerts();
    fetchHistory();
}, 60000);
