import requests
import json
import os
from playwright.sync_api import sync_playwright
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.llms.openai import OpenAI
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.core.agent import ReActAgent
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import sseclient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

FORMS_URL = "https://courts.ca.gov/rules-forms/find-your-court-forms"
OUTPUT_JSON = "court_forms.json"
LLM_API_URL = os.getenv('LLM_API_URL', 'https://api.gmi-serving.com/v1/chat/completions')
LLM_API_KEY = os.getenv('LLM_API_KEY')

if not LLM_API_KEY:
    print("⚠️  Warning: LLM_API_KEY not set in environment variables. LLM features will be disabled.")


def crawl_court_forms():
    """Crawl the California Courts forms page and extract form titles and URLs."""
    forms = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(FORMS_URL)
        page.wait_for_load_state("networkidle")
        # Extract form links (adjust selector as needed)
        links = page.query_selector_all("a[href*='forms/']")
        for link in links:
            title = link.inner_text().strip()
            url = link.get_attribute("href")
            if url and title:
                if not url.startswith("http"):
                    url = "https://courts.ca.gov" + url
                forms.append({"title": title, "url": url})
        browser.close()
    # Save to JSON
    with open(OUTPUT_JSON, "w") as f:
        json.dump(forms, f, indent=2)
    print(f"Extracted {len(forms)} forms and saved to {OUTPUT_JSON}")
    return forms


def load_forms():
    with open(OUTPUT_JSON, "r") as f:
        return json.load(f)


def find_relevant_forms(query, forms, top_k=5):
    """Simple keyword search for relevant forms."""
    query_lower = query.lower()
    scored = [
        (form, sum(word in form["title"].lower() for word in query_lower.split()))
        for form in forms
    ]
    # Sort by score (descending) and return top_k
    relevant = [form for form, score in sorted(scored, key=lambda x: -x[1]) if score > 0]
    return relevant[:top_k] if relevant else forms[:top_k]


def ask_llm(user_question, context_forms):
    context = "\n".join(f"- {f['title']}: {f['url']}" for f in context_forms)
    prompt = (
        "You are a helpful AI assistant. Given the following court forms and a user question, "
        "suggest which form(s) are most relevant and what information the user needs to fill out. "
        "For each form you mention, include its full name and the direct URL if available from the provided list.\n"
        f"Court Forms:\n{context}\n\nQuestion: {user_question}"
    )
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer <YOUR_TOKEN>"
    }
    data = {
        "model": "deepseek-ai/DeepSeek-R1-0528",
        "messages": [
            {"role": "system", "content": "You are a helpful AI assistant"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0,
        "max_tokens": 500
    }
    response = requests.post("https://api.gmi-serving.com/v1/chat/completions", headers=headers, json=data)
    response.raise_for_status()
    resp_json = response.json()
    msg = resp_json["choices"][0]["message"]
    return msg.get("content") or msg.get("reasoning_content") or "No valid answer found."


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Legal agent for CA court forms.")
    parser.add_argument("--crawl", action="store_true", help="Crawl and update court forms list.")
    parser.add_argument("--ask", type=str, help="Ask a question about court forms.")
    args = parser.parse_args()

    if args.crawl:
        crawl_court_forms()
    if args.ask:
        forms = load_forms()
        relevant = find_relevant_forms(args.ask, forms)
        answer = ask_llm(args.ask, relevant)
        print("\nLLM Answer:\n", answer)

if __name__ == "__main__":
    main()

# Suppose you have a directory with .txt files, one per form
docs = SimpleDirectoryReader(input_dir="./forms_txt").load_data()
index = VectorStoreIndex.from_documents(docs)
index.storage_context.persist(persist_dir="./storage/forms")

llm = OpenAI(model="gpt-4")
engine = index.as_query_engine(similarity_top_k=3, llm=llm)

query_engine_tool = QueryEngineTool(
    query_engine=engine,
    metadata=ToolMetadata(
        name="court_forms",
        description="Provides information about California court forms. Use a detailed legal question as input."
    ),
)

agent = ReActAgent.from_tools([query_engine_tool], llm=llm, verbose=True)

# Load index and forms
index = faiss.read_index("forms.index")
with open("forms_texts.json") as f:
    form_texts = json.load(f)
with open("court_forms.json") as f:
    forms = json.load(f)

model = SentenceTransformer("all-MiniLM-L6-v2")

def retrieve_relevant_forms(query, top_k=5):
    query_emb = model.encode([query])
    D, I = index.search(np.array(query_emb).astype("float32"), top_k)
    return [forms[i] for i in I[0]]

# Example usage
user_question = "I want to file for child custody in California"
relevant_forms = retrieve_relevant_forms(user_question)
answer = ask_llm(user_question, relevant_forms)
print(answer)

# Connect to the SSE endpoint
response = requests.get("http://localhost:8051/sse", stream=True)
client = sseclient.SSEClient(response)

for event in client.events():
    print(f"Event: {event.event}")
    print(f"Data: {event.data}")

# 1. Open SSE connection
sse_url = "http://localhost:8051/sse"
response = requests.get(sse_url, stream=True)
client = sseclient.SSEClient(response)

# 2. Get the /messages/ endpoint from the first event
for event in client.events():
    print(f"Event: {event.event}")
    print(f"Data: {event.data}")
    if event.event == "endpoint":
        # The server tells you where to send messages
        session_id = event.data.strip()
        messages_url = f"http://localhost:8051/messages/?session_id={session_id}"
        break

# 3. Send a command (e.g., smart_crawl_url)
payload = {
    "command": "smart_crawl_url",
    "url": "https://courts.ca.gov/rules-forms/find-your-court-forms"
}
headers = {"Content-Type": "application/json"}
resp = requests.post(messages_url, data=json.dumps(payload), headers=headers)
print("Command response:", resp.text)

# 4. Continue listening for results/events
for event in client.events():
    print(f"Event: {event.event}")
    print(f"Data: {event.data}") 