# California Legal Forms Assistant - Frontend

A beautiful, modern web interface for the California Legal Forms Assistant that provides natural language search capabilities for legal guidance.

## Features

🎯 **Natural Language Search**: Ask questions in plain English about California legal procedures
📋 **Smart Form Recommendations**: Get specific form codes and purposes
📝 **Step-by-Step Guidance**: Detailed instructions for legal processes
🔗 **Resource Links**: Direct links to official California Courts resources
⚡ **Real-time Search**: Powered by MCP server with advanced crawling and RAG capabilities
🎨 **Modern UI**: Beautiful, responsive design with intuitive navigation

## Quick Start

1. **Start the MCP Server** (in another terminal):
   ```bash
   cd ../mcp-crawl4ai-rag
   source .venv/bin/activate
   export SUPABASE_URL="https://qomnyvidjpoblqbipyjd.supabase.co"
   export SUPABASE_SERVICE_KEY="your-service-key"
   python src/crawl4ai_mcp.py
   ```

2. **Start the Frontend**:
   ```bash
   cd frontend
   python3 start_frontend.py
   ```

3. **Open your browser** and go to: http://localhost:5000

## Usage

### Natural Language Questions
Ask questions like:
- "How do I file for divorce in California?"
- "What forms do I need for child custody?"
- "How do I modify child support?"
- "What's the process for adoption?"

### Quick Questions
Click on the pre-defined quick question buttons for common legal scenarios:
- **Divorce Process**
- **Child Custody**
- **Child Support**
- **Adoption**
- **Restraining Order**

### Admin Functions
Use the admin panel to:
- **Crawl Forms**: Basic crawling of the court forms page
- **Smart Crawl**: Advanced crawling with depth control
- **Check Sources**: View available data sources

## API Endpoints

- `POST /api/ask` - Ask legal questions
- `POST /api/search` - Search for specific forms
- `POST /api/crawl` - Trigger crawling
- `GET /api/sources` - Get available sources

## Technology Stack

- **Backend**: Flask + Python
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **Icons**: Font Awesome 6
- **Integration**: MCP Server with Supabase
- **Styling**: Modern gradient design with responsive layout

## Example Questions

### Divorce
- "What forms do I need to file for divorce?"
- "How long does divorce take in California?"
- "What are the residency requirements for divorce?"

### Child Custody
- "How do I get custody of my children?"
- "What factors do courts consider for custody?"
- "Can I modify a custody order?"

### Support
- "How is child support calculated?"
- "How do I request spousal support?"
- "Can I modify support payments?"

## Response Format

The system provides structured responses with:
- **Description**: Overview of the legal process
- **Required Forms**: Specific form codes and purposes
- **Steps**: Detailed step-by-step instructions
- **Requirements**: Legal requirements and considerations
- **Resources**: Links to official California Courts pages

## Development

To modify the frontend:
1. Edit `app.py` for backend API changes
2. Modify the HTML template in `start_frontend.py`
3. Restart the server to see changes

## Troubleshooting

- **Server not starting**: Check if port 5000 is available
- **MCP connection issues**: Ensure MCP server is running on port 8051
- **No search results**: Trigger crawling using admin buttons
- **API errors**: Check browser console for detailed error messages 