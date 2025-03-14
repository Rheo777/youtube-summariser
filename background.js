chrome.contextMenus.create({
  id: "summarizeText",
  title: "Summarize Selected Text",
  contexts: ["selection"]
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "summarizeText") {
    const selectedText = info.selectionText;
    
    fetch('http://localhost:5000/summarize', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ text: selectedText })
    })
    .then(response => response.json())
    .then(data => {
      chrome.runtime.sendMessage({
        action: "updateSummary",
        summary: data.summary
      });
    })
    .catch(error => {
      chrome.runtime.sendMessage({
        action: "updateSummary",
        summary: "Error: " + error.message
      });
    });
  }
}); 