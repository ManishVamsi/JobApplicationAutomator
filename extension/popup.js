/**
 * Popup Script — Settings & Status UI
 */

document.addEventListener('DOMContentLoaded', async () => {
  const apiUrlInput = document.getElementById('apiUrl');
  const apiTokenInput = document.getElementById('apiToken');
  const tokenPrefixEl = document.getElementById('tokenPrefix');
  const saveBtn = document.getElementById('saveBtn');
  const testBtn = document.getElementById('testBtn');
  const statusEl = document.getElementById('status');
  const statusTextEl = document.getElementById('statusText');
  const postCountEl = document.getElementById('postCount');
  const lastPostEl = document.getElementById('lastPost');

  // Load saved settings
  const stored = await chrome.storage.local.get([
    'apiUrl', 'apiToken', 'sessionPostCount', 'lastPostAt',
  ]);

  if (stored.apiUrl) apiUrlInput.value = stored.apiUrl;
  if (stored.apiToken) {
    apiTokenInput.value = ''; // Don't show full token
    apiTokenInput.placeholder = '••• saved •••';
    const prefix = stored.apiToken.substring(0, 8) + '...';
    tokenPrefixEl.textContent = prefix;
    tokenPrefixEl.style.display = 'block';
  }

  // Stats
  postCountEl.textContent = stored.sessionPostCount || '0';
  if (stored.lastPostAt) {
    const ago = getTimeAgo(new Date(stored.lastPostAt));
    lastPostEl.textContent = ago;
    lastPostEl.style.fontSize = '12px';
  }

  // Save
  saveBtn.addEventListener('click', async () => {
    const apiUrl = apiUrlInput.value.trim().replace(/\/$/, '');
    const apiToken = apiTokenInput.value.trim();

    if (!apiUrl) {
      setStatus('error', 'API URL is required');
      return;
    }

    const toSave = { apiUrl };
    if (apiToken) toSave.apiToken = apiToken;

    await chrome.storage.local.set(toSave);
    setStatus('connected', 'Settings saved');

    if (apiToken) {
      const prefix = apiToken.substring(0, 8) + '...';
      tokenPrefixEl.textContent = prefix;
      tokenPrefixEl.style.display = 'block';
      apiTokenInput.value = '';
      apiTokenInput.placeholder = '••• saved •••';
    }
  });

  // Test Connection
  testBtn.addEventListener('click', async () => {
    setStatus('idle', 'Testing...');
    try {
      const response = await new Promise((resolve, reject) => {
        chrome.runtime.sendMessage({ type: 'TEST_CONNECTION' }, (res) => {
          if (chrome.runtime.lastError) {
            reject(new Error(chrome.runtime.lastError.message));
          } else if (res?.success) {
            resolve(res);
          } else {
            reject(new Error(res?.error || 'Connection failed'));
          }
        });
      });
      setStatus('connected', '✓ Connected');
    } catch (err) {
      setStatus('error', err.message);
    }
  });

  function setStatus(type, text) {
    statusEl.className = `status status-${type}`;
    statusTextEl.textContent = text;
  }

  function getTimeAgo(date) {
    const seconds = Math.floor((new Date() - date) / 1000);
    if (seconds < 60) return 'just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
  }
});
