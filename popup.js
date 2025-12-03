document.getElementById("getLinks").addEventListener("click", async () => {
  let [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !tab.id) return;

  chrome.scripting.executeScript(
    {
      target: { tabId: tab.id },
      func: () => {
        const anchors = document.querySelectorAll("a[href]");
        let links = [];
        anchors.forEach(a => {
          const href = a.href.toLowerCase();
          if (href.includes("privacy") || href.includes("policy") || href.includes("terms")) {
            links.push(href);
          }
        });
        return [...new Set(links)];
      }
    },
    (results) => {
      const container = document.getElementById("linkContainer");
      container.innerHTML = "";
      document.getElementById("resultContainer").innerHTML = "";

      if (results && results[0].result.length > 0) {
        // hide fetch button
        document.getElementById("getLinks").style.display = "none";

        results[0].result.forEach(link => {
          const btn = document.createElement("button");
          btn.textContent = link;
          btn.className = "link-btn";
          btn.addEventListener("click", () => runAnalysis(link, btn));
          container.appendChild(btn);
        });
      } else {
        container.innerHTML = "<center><p>No privacy/terms links found.</p></center>";
      }
    }
  );
});

async function runAnalysis(link, btn) {
  // hide all other buttons once one is clicked
  const allButtons = document.querySelectorAll(".link-btn");
  allButtons.forEach(b => {
    if (b !== btn) {
      b.style.display = "none"; // or b.disabled = true if you want to grey them out
    }
  });

  // create result box below the clicked button
  let resultBox = document.createElement("div");
  resultBox.className = "result-box";
  resultBox.innerHTML = `<p>Analyzing...</p>`;
  btn.insertAdjacentElement("afterend", resultBox);

  try {
    const res = await fetch("http://127.0.0.1:8000/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: link })
    });

    
    const data = await res.json();
    resultBox.innerHTML = `
      <p><strong>Status:</strong> ${data.status}</p>
      <p><strong>Dark Patterns:</strong> ${
  data.dark_patterns.length > 0 
    ? data.dark_patterns.map(dp => `${dp.keyword} → ${dp.meaning}`).join("<br>")
    : "None"
}</p>

<p><strong>Hidden Clauses:</strong> ${
  data.hidden_clauses.length > 0 
    ? data.hidden_clauses.map(hc => `${hc.keyword} → ${hc.meaning}`).join("<br>")
    : "None"
}</p>
    `;
  } catch (err) {
    resultBox.innerHTML = `<span style="color:red;">Error contacting backend</span>`;
  }
}

