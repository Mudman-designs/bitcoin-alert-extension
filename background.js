const BACKEND_URL = 'https://bitcoin-alert-extension.onrender.com';
let lastPrice = null;
let notificationHistory = [];

console.log('Background service worker started!');

// Check price every 60 seconds instead of 30 to reduce API calls
chrome.alarms.create('priceCheck', { periodInMinutes: 1 });

chrome.alarms.onAlarm.addListener((alarm) => {
    console.log('Alarm triggered:', alarm.name);
    if (alarm.name === 'priceCheck') {
        checkPriceAndAlerts();
    }
});

async function checkPriceAndAlerts() {
    console.log('Checking price and alerts...');
    
    try {
        const response = await fetch(`${BACKEND_URL}/api/check_alerts`);
        
        if (!response.ok) {
            console.error('Backend returned error:', response.status);
            const errorText = await response.text();
            console.error('Error details:', errorText);
            return;
        }
        
        const data = await response.json();
        console.log('Check alerts response:', data);
        
        if (data.triggered_alerts && data.triggered_alerts.length > 0) {
            console.log('Triggered alerts found!', data.triggered_alerts);
            data.triggered_alerts.forEach(alert => {
                sendNotification(alert, data.current_price);
            });
        } else {
            console.log('No triggered alerts');
        }
        lastPrice = data.current_price;
    } catch (error) {
        console.error('Background check error:', error);
    }
}

function sendNotification(alert, currentPrice) {
    console.log('Sending notification for alert:', alert);
    
    let message = '';
    let title = '💰 Bitcoin Alert';
    
    if (alert.reason && alert.reason.includes('below')) {
        message = `BTC dropped ${alert.reason}!\nCurrent: $${currentPrice.toLocaleString()}`;
        title = '📉 Bitcoin Dropped!';
    } else if (alert.reason && alert.reason.includes('above')) {
        message = `BTC surged ${alert.reason}!\nCurrent: $${currentPrice.toLocaleString()}`;
        title = '📈 Bitcoin Surged!';
    } else if (alert.reason && alert.reason.includes('volume')) {
        message = `📊 ${alert.reason}!\nCurrent: $${currentPrice.toLocaleString()}`;
        title = '📊 Volume Spike!';
    } else if (alert.reason && alert.reason.includes('volatility')) {
        message = `⚡ ${alert.reason}!\nCurrent: $${currentPrice.toLocaleString()}`;
        title = '⚡ Volatility Alert!';
    } else if (alert.reason && alert.reason.includes('RSI')) {
        message = `📈 ${alert.reason}!\nCurrent: $${currentPrice.toLocaleString()}`;
        title = '📈 RSI Alert!';
    } else if (alert.reason && alert.reason.includes('Golden Cross')) {
        message = `🔀 ${alert.reason}!\nCurrent: $${currentPrice.toLocaleString()}`;
        title = '🔀 Golden Cross Alert!';
    } else {
        message = `BTC price alert triggered!\nCurrent: $${currentPrice.toLocaleString()}`;
    }
    
    const notificationId = `btc-alert-${Date.now()}`;
    
    const historyEntry = {
        id: notificationId,
        title: title,
        message: message,
        price: currentPrice,
        type: alert.type || 'price',
        timestamp: new Date().toLocaleString(),
        read: false
    };
    notificationHistory.unshift(historyEntry);
    
    if (notificationHistory.length > 50) {
        notificationHistory = notificationHistory.slice(0, 50);
    }
    
    chrome.storage.local.set({ notificationHistory: notificationHistory }, () => {
        console.log('Notification history saved');
    });
    
    const minimalIcon = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==';
    
    const options = {
        type: 'basic',
        iconUrl: minimalIcon,
        title: title,
        message: message,
        priority: 2,
        requireInteraction: true,
        silent: false,
        buttons: [
            { title: '📊 View Details' }
        ]
    };
    
    chrome.notifications.create(notificationId, options, (id) => {
        if (chrome.runtime.lastError) {
            console.error('Notification error:', chrome.runtime.lastError.message);
        } else {
            console.log('✅ Notification sent! ID:', id);
        }
    });
}

chrome.notifications.onButtonClicked.addListener((notificationId, buttonIndex) => {
    console.log('Notification button clicked:', notificationId, buttonIndex);
    openExtensionPopup();
});

chrome.notifications.onClicked.addListener((notificationId) => {
    console.log('Notification clicked:', notificationId);
    openExtensionPopup();
});

chrome.notifications.onClosed.addListener((notificationId, byUser) => {
    console.log('Notification closed:', notificationId, 'by user:', byUser);
    if (byUser) {
        const alert = notificationHistory.find(n => n.id === notificationId);
        if (alert) {
            alert.read = true;
            chrome.storage.local.set({ notificationHistory: notificationHistory });
        }
    }
});

function openExtensionPopup() {
    const unread = notificationHistory.filter(n => !n.read);
    unread.forEach(n => n.read = true);
    if (unread.length > 0) {
        chrome.storage.local.set({ notificationHistory: notificationHistory });
    }
    
    chrome.action.openPopup().catch(() => {
        chrome.tabs.create({
            url: chrome.runtime.getURL('popup.html')
        });
    });
}

// Initial check
setTimeout(() => {
    console.log('Initial check...');
    checkPriceAndAlerts();
    chrome.storage.local.get(['notificationHistory'], (result) => {
        if (result.notificationHistory) {
            notificationHistory = result.notificationHistory;
            console.log('Loaded notification history:', notificationHistory.length);
        }
    });
}, 3000);

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log('Message received:', request);
    if (request.action === 'getStatus') {
        sendResponse({ lastPrice: lastPrice });
    } else if (request.action === 'getHistory') {
        sendResponse({ history: notificationHistory });
    } else if (request.action === 'clearHistory') {
        notificationHistory = [];
        chrome.storage.local.set({ notificationHistory: [] }, () => {
            sendResponse({ success: true });
        });
        return true;
    }
});

console.log('✅ Background service worker ready!');
