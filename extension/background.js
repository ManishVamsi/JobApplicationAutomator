/**
 * Background Service Worker — API Relay
 *
 * Receives hiring posts from the content script and forwards them
 * to the backend via the extension API token.
 */

// ─── Message Handler ───────────────────────────────────────────
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === 'LINKEDIN_HIRING_POST') {
    forwardPost(message.payload)
      .then((result) => sendResponse({ success: true, ...result }))
      .catch((error) => sendResponse({ success: false, error: error.message }));
    return true; // Keep message channel open for async response
  }

  if (message.type === 'TEST_CONNECTION') {
    testConnection()
      .then((result) => sendResponse({ success: true, ...result }))
      .catch((error) => sendResponse({ success: false, error: error.message }));
    return true;
  }
});

// ─── API Calls ─────────────────────────────────────────────────
async function getConfig() {
  const result = await chrome.storage.local.get(['apiUrl', 'apiToken']);
  if (!result.apiUrl || !result.apiToken) {
    throw new Error('Extension not configured. Open settings and enter your API URL and token.');
  }
  return { apiUrl: result.apiUrl, apiToken: result.apiToken };
}

async function forwardPost(payload) {
  const { apiUrl, apiToken } = await getConfig();

  const response = await fetch(`${apiUrl}/api/v1/linkedin-posts/ingest`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiToken}`,
    },
    body: JSON.stringify(payload),
  });

  if (response.status === 429) {
    console.warn('[JAA] Rate limited — backing off');
    return { rateLimited: true };
  }

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`API error ${response.status}: ${text}`);
  }

  const data = await response.json();

  // Track session stats
  const stats = await chrome.storage.local.get(['sessionPostCount']);
  await chrome.storage.local.set({
    sessionPostCount: (stats.sessionPostCount || 0) + 1,
    lastPostAt: new Date().toISOString(),
  });

  return data;
}

async function testConnection() {
  const { apiUrl, apiToken } = await getConfig();

  const response = await fetch(`${apiUrl}/api/v1/healthz`, {
    headers: { 'Authorization': `Bearer ${apiToken}` },
  });

  if (!response.ok) {
    throw new Error(`Connection failed: ${response.status}`);
  }

  return { connected: true };
}
