function getYouTubeVideoId(url) {
    try {
        const urlObj = new URL(url);
        if (urlObj.hostname.includes('youtube.com')) {
            return urlObj.searchParams.get('v');
        } else if (urlObj.hostname.includes('youtu.be')) {
            return urlObj.pathname.slice(1);
        }
    } catch (error) {
        console.error('URL parsing error:', error);
    }
    return null;
}

function showError(message) {
    console.log('Showing error:', message);
    document.getElementById('loading').style.display = 'none';
    document.getElementById('error').textContent = message;
    document.getElementById('error').style.display = 'block';
}

function showSummary(summary) {
    console.log('Showing summary');
    document.getElementById('loading').style.display = 'none';
    document.getElementById('error').style.display = 'none';
    document.getElementById('summary').textContent = summary;
    document.getElementById('summary').style.display = 'block';
}

function showLoading() {
    console.log('Showing loading');
    document.getElementById('loading').style.display = 'block';
    document.getElementById('error').style.display = 'none';
    document.getElementById('summary').style.display = 'none';
}

// When popup opens
document.addEventListener('DOMContentLoaded', function() {
    showLoading();
    
    // Get current tab URL
    chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
        if (!tabs || !tabs[0] || !tabs[0].url) {
            showError('Cannot access current tab');
            return;
        }

        const currentUrl = tabs[0].url;
        console.log('Current URL:', currentUrl);
        
        const videoId = getYouTubeVideoId(currentUrl);
        console.log('Video ID:', videoId);
        
        if (!videoId) {
            showError('Not a YouTube video page');
            return;
        }
        
        // Send request to our API
        const requestData = { video_id: videoId };
        console.log('Sending request:', requestData);
        
        fetch('http://localhost:5001/summarize-youtube', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            mode: 'cors',
            body: JSON.stringify(requestData)
        })
        .then(async response => {
            console.log('Response status:', response.status);
            console.log('Response headers:', [...response.headers.entries()]);
            console.log('Response URL:', response.url);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const text = await response.text();
            console.log('Raw response:', text);
            
            if (!text) {
                throw new Error('Empty response from server');
            }
            
            try {
                return JSON.parse(text);
            } catch (e) {
                throw new Error(`Invalid JSON: ${text.substring(0, 100)}...`);
            }
        })
        .then(data => {
            console.log('Processed data:', data);
            if (data.error) {
                showError(data.error);
            } else if (data.summary) {
                showSummary(data.summary);
            } else {
                showError('Invalid response from server');
            }
        })
        .catch(error => {
            console.error('Detailed error:', error);
            console.error('Error stack:', error.stack);
            showError(`Error: ${error.message}`);
        });
    });
}); 