#!/usr/bin/env python3
import os
from app import app

# Create the HTML template if it doesn't exist
html_content = '''<!DOCTYPE html>
<html>
<head>
    <title>California Legal Forms Assistant</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body { font-family: Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); margin: 0; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { text-align: center; color: white; margin-bottom: 30px; }
        .search-section { background: white; border-radius: 20px; padding: 30px; margin-bottom: 30px; }
        .search-input { width: 100%; padding: 15px; font-size: 1.1rem; border: 2px solid #ddd; border-radius: 10px; margin-bottom: 15px; }
        .search-btn { background: #667eea; color: white; border: none; padding: 15px 30px; border-radius: 10px; cursor: pointer; }
        .quick-questions { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 20px; }
        .quick-question { background: #f8f9ff; border: 1px solid #ddd; padding: 10px 15px; border-radius: 25px; cursor: pointer; }
        .quick-question:hover { background: #667eea; color: white; }
        .results { display: none; background: white; border-radius: 20px; padding: 30px; margin-bottom: 30px; }
        .form-card { background: #f8f9ff; border: 2px solid #ddd; border-radius: 15px; padding: 20px; margin: 10px 0; }
        .form-code { background: #667eea; color: white; padding: 5px 12px; border-radius: 20px; font-weight: bold; display: inline-block; margin-bottom: 10px; }
        .admin-section { background: white; border-radius: 20px; padding: 30px; }
        .admin-btn { background: #764ba2; color: white; border: none; padding: 12px 20px; border-radius: 10px; cursor: pointer; margin: 5px; }
        .loading { display: none; text-align: center; padding: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1><i class="fas fa-balance-scale"></i> California Legal Forms Assistant</h1>
            <p>Get expert guidance on California court forms and legal procedures</p>
        </div>
        <div class="search-section">
            <input type="text" id="searchInput" class="search-input" placeholder="Ask me anything about California legal forms...">
            <button id="searchBtn" class="search-btn"><i class="fas fa-search"></i> Search</button>
            <div class="quick-questions">
                <div class="quick-question" data-question="How do I file for divorce in California?">Divorce Process</div>
                <div class="quick-question" data-question="What forms do I need for child custody?">Child Custody</div>
                <div class="quick-question" data-question="How do I modify child support?">Child Support</div>
                <div class="quick-question" data-question="What forms are needed for adoption?">Adoption</div>
            </div>
        </div>
        <div class="loading" id="loading"><i class="fas fa-spinner fa-spin"></i><p>Searching legal database...</p></div>
        <div class="results" id="results">
            <h2 id="resultTitle">Legal Guidance</h2>
            <div id="guidanceDescription"></div>
            <div id="formsContainer"></div>
            <div id="stepsContainer"></div>
            <div id="requirementsContainer"></div>
            <div id="linksContainer"></div>
        </div>
        <div class="admin-section">
            <h2><i class="fas fa-cogs"></i> System Administration</h2>
            <button class="admin-btn" id="crawlBtn"><i class="fas fa-spider"></i> Crawl Forms</button>
            <button class="admin-btn" id="smartCrawlBtn"><i class="fas fa-brain"></i> Smart Crawl</button>
            <button class="admin-btn" id="sourcesBtn"><i class="fas fa-database"></i> Check Sources</button>
            <div id="statusMessage" style="margin-top: 15px; padding: 10px; border-radius: 5px; display: none;"></div>
        </div>
    </div>
    <script>
        const searchInput = document.getElementById("searchInput");
        const searchBtn = document.getElementById("searchBtn");
        const loading = document.getElementById("loading");
        const results = document.getElementById("results");
        const quickQuestions = document.querySelectorAll(".quick-question");
        const statusMessage = document.getElementById("statusMessage");
        
        async function performSearch(question) {
            if (!question.trim()) return;
            loading.style.display = "block";
            results.style.display = "none";
            try {
                const response = await fetch("/api/ask", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ question: question })
                });
                const data = await response.json();
                if (data.error) throw new Error(data.error);
                displayResults(data);
            } catch (error) {
                console.error("Error:", error);
                showStatus("Error: " + error.message, "error");
            } finally {
                loading.style.display = "none";
            }
        }
        
        function displayResults(data) {
            const guidance = data.guidance;
            document.getElementById("resultTitle").textContent = "Guidance for: \\"" + data.question + "\\"";
            document.getElementById("guidanceDescription").innerHTML = "<p>" + guidance.description + "</p>";
            
            const formsContainer = document.getElementById("formsContainer");
            if (guidance.forms && guidance.forms.length > 0) {
                formsContainer.innerHTML = "<h3>Required Forms:</h3>" +
                    guidance.forms.map(form => 
                        "<div class=\\"form-card\\">" +
                            "<div class=\\"form-code\\">" + form.code + "</div>" +
                            "<div><strong>" + form.name + "</strong></div>" +
                            "<div>" + form.purpose + "</div>" +
                        "</div>"
                    ).join("");
            }
            
            const stepsContainer = document.getElementById("stepsContainer");
            if (guidance.steps && guidance.steps.length > 0) {
                stepsContainer.innerHTML = "<h3>Steps to Follow:</h3><ol>" +
                    guidance.steps.map(step => "<li>" + step + "</li>").join("") + "</ol>";
            }
            
            const requirementsContainer = document.getElementById("requirementsContainer");
            if (guidance.requirements && guidance.requirements.length > 0) {
                requirementsContainer.innerHTML = "<h3>Requirements:</h3><ul>" +
                    guidance.requirements.map(req => "<li>" + req + "</li>").join("") + "</ul>";
            }
            
            const linksContainer = document.getElementById("linksContainer");
            if (guidance.links && guidance.links.length > 0) {
                linksContainer.innerHTML = "<h3>Helpful Resources:</h3>" +
                    guidance.links.map(link => 
                        "<p><a href=\\"" + link.url + "\\" target=\\"_blank\\">" + link.text + "</a></p>"
                    ).join("");
            }
            
            results.style.display = "block";
        }
        
        function showStatus(message, type) {
            statusMessage.textContent = message;
            statusMessage.style.backgroundColor = type === "error" ? "#f8d7da" : "#d4edda";
            statusMessage.style.color = type === "error" ? "#721c24" : "#155724";
            statusMessage.style.display = "block";
            setTimeout(() => statusMessage.style.display = "none", 5000);
        }
        
        searchBtn.addEventListener("click", () => performSearch(searchInput.value));
        searchInput.addEventListener("keypress", (e) => {
            if (e.key === "Enter") performSearch(searchInput.value);
        });
        
        quickQuestions.forEach(question => {
            question.addEventListener("click", () => {
                const questionText = question.getAttribute("data-question");
                searchInput.value = questionText;
                performSearch(questionText);
            });
        });
        
        document.getElementById("crawlBtn").addEventListener("click", async () => {
            try {
                await fetch("/api/crawl", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ type: "single" })
                });
                showStatus("Crawling started successfully!", "success");
            } catch (error) {
                showStatus("Error starting crawl: " + error.message, "error");
            }
        });
        
        document.getElementById("smartCrawlBtn").addEventListener("click", async () => {
            try {
                await fetch("/api/crawl", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ type: "smart" })
                });
                showStatus("Smart crawling started successfully!", "success");
            } catch (error) {
                showStatus("Error starting smart crawl: " + error.message, "error");
            }
        });
        
        document.getElementById("sourcesBtn").addEventListener("click", async () => {
            try {
                const response = await fetch("/api/sources");
                const data = await response.json();
                showStatus("Sources checked - see console for details", "success");
                console.log("Available sources:", data);
            } catch (error) {
                showStatus("Error checking sources: " + error.message, "error");
            }
        });
    </script>
</body>
</html>'''

# Write the HTML template
os.makedirs('templates', exist_ok=True)
with open('templates/index.html', 'w') as f:
    f.write(html_content)

print("✅ HTML template created successfully!")
print("🚀 Starting Flask server...")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 