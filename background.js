// Listen for messages from popup or content scripts
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === "getLinksFromTab") {
    chrome.scripting.executeScript({
      target: { tabId: sender.tab.id },
      files: ["content.js"]
    }, () => {
      sendResponse({ status: "content script injected" });
    });
    return true; // keeps channel open for async response
  }
});
