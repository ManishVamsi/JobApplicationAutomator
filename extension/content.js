/**
 * Content Script — LinkedIn Hiring Post Detector
 *
 * Runs on LinkedIn feed/profile pages. Uses MutationObserver to detect
 * new posts containing hiring-related keywords, extracts metadata,
 * and forwards to the background service worker for API relay.
 */

(() => {
  'use strict';

  // ─── Configuration ───────────────────────────────────────────
  const HIRING_PATTERNS = [
    /\b(we'?re|i'?m|we are|i am)\s+hiring\b/i,
    /\b(looking for|seeking|searching for)\s+(a|an)?\s*(senior|junior|mid|staff|lead|principal)?\s*(software|frontend|backend|fullstack|full-stack|devops|sre|data|ml|ai|cloud|mobile|ios|android|web|react|node|python|java|go|rust|c\+\+|engineer|developer|architect|manager|designer|analyst|scientist)\b/i,
    /\bopen\s+(position|role|roles|opportunity|opportunities)\b/i,
    /\b(dm|send|share)\s+(me\s+)?(your\s+)?(resume|cv|portfolio)\b/i,
    /\bapply\s+(now|here|today|below)\b/i,
    /\bjob\s+(opening|alert|opportunity)\b/i,
    /\b(join\s+(our|my)\s+team)\b/i,
    /\b#hiring\b/i,
    /\b#jobopening\b/i,
    /\b#opentowork\b/i,
  ];

  const MIN_POST_LENGTH = 50;
  const MAX_POST_LENGTH = 2000;
  const DEBOUNCE_MS = 500;

  // ─── State ───────────────────────────────────────────────────
  const sentUrls = new Set();
  let debounceTimer = null;
  let sessionCount = 0;

  // ─── Helpers ─────────────────────────────────────────────────
  function getPostUrl(postElement) {
    // Try to find the permalink in the post
    const timeLink = postElement.querySelector('a[href*="/feed/update/"]');
    if (timeLink) return timeLink.href.split('?')[0];

    const activityLink = postElement.querySelector('a[href*="/activity/"]');
    if (activityLink) return activityLink.href.split('?')[0];

    return null;
  }

  function getPosterName(postElement) {
    const nameEl = postElement.querySelector(
      '.update-components-actor__title span[aria-hidden="true"], ' +
      '.feed-shared-actor__title span[aria-hidden="true"], ' +
      '.update-components-actor__name span[aria-hidden="true"]'
    );
    return nameEl ? nameEl.textContent.trim() : null;
  }

  function getPostText(postElement) {
    const textEl = postElement.querySelector(
      '.feed-shared-update-v2__description, ' +
      '.update-components-text, ' +
      '.feed-shared-text, ' +
      '[data-test-id="main-feed-activity-card__commentary"]'
    );
    if (!textEl) return '';
    return textEl.textContent.trim().slice(0, MAX_POST_LENGTH);
  }

  function isHiringPost(text) {
    if (text.length < MIN_POST_LENGTH) return false;
    return HIRING_PATTERNS.some((pattern) => pattern.test(text));
  }

  // ─── Post Processing ────────────────────────────────────────
  function processPost(postElement) {
    const text = getPostText(postElement);
    if (!isHiringPost(text)) return;

    const url = getPostUrl(postElement);
    if (url && sentUrls.has(url)) return; // Already sent this session

    const posterName = getPosterName(postElement);

    // Mark as sent
    if (url) sentUrls.add(url);

    // Forward to background
    chrome.runtime.sendMessage({
      type: 'LINKEDIN_HIRING_POST',
      payload: {
        post_url: url,
        raw_text: text,
        poster_name: posterName,
      },
    });

    sessionCount++;

    // Visual indicator on the post
    if (!postElement.dataset.jaaDetected) {
      postElement.dataset.jaaDetected = 'true';
      postElement.style.borderLeft = '3px solid #6366f1';
    }
  }

  // ─── Observer ────────────────────────────────────────────────
  function scanPosts() {
    const posts = document.querySelectorAll(
      '.feed-shared-update-v2, ' +
      '[data-id*="urn:li:activity:"], ' +
      '.occludable-update'
    );
    posts.forEach(processPost);
  }

  function debouncedScan() {
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(scanPosts, DEBOUNCE_MS);
  }

  // Watch for new posts loaded via infinite scroll
  const observer = new MutationObserver((mutations) => {
    let hasNewNodes = false;
    for (const mutation of mutations) {
      if (mutation.addedNodes.length > 0) {
        hasNewNodes = true;
        break;
      }
    }
    if (hasNewNodes) debouncedScan();
  });

  // Start observing the feed container
  function startObserving() {
    const feedContainer = document.querySelector(
      '.scaffold-finite-scroll, ' +
      '.core-rail, ' +
      'main'
    );
    if (feedContainer) {
      observer.observe(feedContainer, {
        childList: true,
        subtree: true,
      });
      // Initial scan
      scanPosts();
      console.log('[JAA] LinkedIn post detector active');
    } else {
      // Feed not loaded yet, retry
      setTimeout(startObserving, 1000);
    }
  }

  startObserving();
})();
