"""
Esempio ispirato dal video by https://www.youtube.com/watch?v=bPNmmDPyGzk

# Create venv and install frameworks
    python -m venv .venv
    source .venv/bin/activate
    cd ./FromOthersSites/BuildRAG
    pip install -r requirements.txt  

# Run
    python app.py

# IA PROMPT 
    all inside BuildRAG, never change others folders. Build a minimal RAG app from this guide:
        https://huggingface.co/learn/cookbook...
        PDF-only
        Extract and chunk roles.pdf text
        Use LangChain
        Use a very small Qwen Instruct
        Save pipeline as app.py . suggest which modules to install in rag_env to match the requirements of app.py . 
    LLMs answers must be short and concise. Design GUI for app.py.
        use Flask. use attached app layout image as inspiration. use logo.png.
        don't change the RAG pipeline itself - just add a GUI in app.py. RAD website like chatgpt look and feel.
"""

import os
import torch
from flask import Flask, render_template_string, request, jsonify, send_from_directory
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_huggingface.llms import HuggingFacePipeline
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# 1. Prepare the data from the PDF
pdf_path = "rules.pdf"
loader = PyPDFLoader(pdf_path)
docs = loader.load()

# Split the PDF text into manageable chunks
splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=50)
chunked_docs = splitter.split_documents(docs)

# 2. Create the embeddings + retriever
# Using BAAI/bge-small-en-v1.5 as a lightweight, performant embedding model
embeddings = HuggingFaceEmbeddings(model_name='BAAI/bge-small-en-v1.5')
db = FAISS.from_documents(chunked_docs, embeddings)

# Retrieve top 4 most similar chunks for context
retriever = db.as_retriever(search_type="similarity", search_kwargs={'k': 4})

# 3. Load quantized or lightweight model
# Using Qwen2.5-0.5B-Instruct as requested. Under 1GB param, very fast and smart.
model_name = "Qwen/Qwen2.5-0.5B-Instruct"

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float16,
    device_map="auto"
)
tokenizer = AutoTokenizer.from_pretrained(model_name)

# 4. Setup the LLM chain
text_generation_pipeline = pipeline(
    model=model,
    tokenizer=tokenizer,
    task="text-generation",
    temperature=0.1,
    do_sample=True,
    repetition_penalty=1.1,
    return_full_text=False, # We don't want to receive the prompt back in the response
    max_new_tokens=400,
)

llm = HuggingFacePipeline(pipeline=text_generation_pipeline)

# Qwen uses ChatML string formats. We structure system-user prompts with proper tokens.
prompt_template = """<|im_start|>system
You are a helpful assistant. Answer the question relying ONLY on the following context. If you don't know the answer, just say that you don't know, do not try to make up an answer. Keep your answers short and concise.

Context:
{context}<|im_end|>
<|im_start|>user
{question}<|im_end|>
<|im_start|>assistant
"""

prompt = PromptTemplate(
    input_variables=["context", "question"],
    template=prompt_template,
)

llm_chain = prompt | llm | StrOutputParser()

# Format the parsed Langchain documents into raw strings for context injection
def format_docs(retrieved_docs):
    return "\n\n".join(doc.page_content for doc in retrieved_docs)

rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | llm_chain
)

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RAG Chat Assistant</title>
    <style>
        body { font-family: 'Inter', -apple-system, sans-serif; background: #343541; color: #ececf1; margin: 0; display: flex; height: 100vh; }
        #sidebar { width: 260px; background: #202123; padding: 10px; display: flex; flex-direction: column; }
        .new-chat-btn { background: transparent; border: 1px solid #565869; color: #ececf1; padding: 12px; border-radius: 6px; cursor: pointer; text-align: left; margin-bottom: 20px; transition: 0.2s; font-size:14px; }
        .new-chat-btn:hover { background: #2A2B32; }
        #chat-container { flex-grow: 1; display: flex; flex-direction: column; position: relative; }
        header { border-bottom: 1px solid rgba(255,255,255,0.1); padding: 10px 20px; font-weight: 500; font-size: 1.2rem; display: flex; align-items: center; justify-content: center; background:#343541;}
        #messages { flex-grow: 1; overflow-y: auto; padding-bottom: 150px; }
        .message { padding: 24px; border-bottom: 1px solid rgba(0,0,0,0.1); display: flex; justify-content: center; }
        .message.bot { background: #444654; }
        .message-content { max-width: 800px; width: 100%; display: flex; gap: 20px; }
        .avatar { width: 30px; height: 30px; border-radius: 4px; object-fit: cover; background: #19c37d; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; overflow: hidden; }
        .avatar img { width: 100%; height: 100%; object-fit: cover; }
        .user-avatar { background: #5436DA; }
        .text { font-size: 1rem; line-height: 1.5; white-space: pre-wrap; width: 100%; }
        #input-area { position: absolute; bottom: 0; left: 0; right: 0; padding: 24px; background: linear-gradient(180deg, rgba(52,53,65,0) 0%, #343541 50%); display: flex; justify-content: center; }
        #input-box { max-width: 800px; width: 100%; background: #40414f; border-radius: 8px; display: flex; box-shadow: 0 0 15px rgba(0,0,0,0.1); padding: 12px; align-items: center; }
        input[type="text"] { flex-grow: 1; background: transparent; border: none; color: white; font-size: 16px; outline: none; padding-left: 10px; }
        button.send-btn { background: transparent; border: none; cursor: pointer; color: #8e8ea0; transition: 0.2s; display: flex; align-items: center; padding: 8px; border-radius:4px; }
        button.send-btn:hover { background: #2A2B32; color: #ececf1; }
        .loading { display: none; margin-left: 50px; color: #8e8ea0; font-style: italic; font-size: 14px; padding-bottom:5px;}
    </style>
</head>
<body>
    <div id="sidebar">
        <button class="new-chat-btn" onclick="document.getElementById('messages').innerHTML = ''; appendMessage('bot', 'Hello! I am ready to answer your questions based on the PDF content. What would you like to know?');">+ New chat</button>
        <div style="flex-grow:1;"></div>
        <div style="padding:10px; font-size: 0.8rem; color: #8e8ea0; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 15px;">BuildRAG API</div>
    </div>
    <div id="chat-container">
        <header>Rapid RAG Assistant</header>
        <div id="messages">
            <div class="message bot">
                <div class="message-content">
                    <div class="avatar"><img src="/logo.png" onerror="this.style.display='none'; this.parentNode.innerText='AI';"></div>
                    <div class="text">Hello! I am ready to answer your questions based on the PDF content. What would you like to know?</div>
                </div>
            </div>
        </div>
        <div id="input-area">
            <div style="width:100%; max-width:800px; display:flex; flex-direction:column; gap:5px;">
                <div class="loading" id="loading-indicator">Thinking...</div>
                <div id="input-box">
                    <input type="text" id="user-input" placeholder="Message RAG Assistant..." autocomplete="off">
                    <button class="send-btn" id="send-btn">
                        <svg stroke="currentColor" fill="none" stroke-width="2" viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round" height="20" width="20" xmlns="http://www.w3.org/2000/svg"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
                    </button>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const msgs = document.getElementById('messages');
        const input = document.getElementById('user-input');
        const btn = document.getElementById('send-btn');
        const loading = document.getElementById('loading-indicator');

        function appendMessage(role, text) {
            const div = document.createElement('div');
            div.className = `message ${role}`;
            
            const avatarContent = role === 'bot' 
                ? '<img src="/logo.png" onerror="this.style.display=\\'none\\'; this.parentNode.innerText=\\'AI\\';">' 
                : 'U';
            const avatarClass = role === 'bot' ? 'avatar' : 'avatar user-avatar';
            
            div.innerHTML = `
                <div class="message-content">
                    <div class="${avatarClass}">${avatarContent}</div>
                    <div class="text">${text}</div>
                </div>
            `;
            msgs.appendChild(div);
            msgs.scrollTop = msgs.scrollHeight;
        }

        async function sendMessage() {
            const text = input.value.trim();
            if (!text) return;
            
            input.value = '';
            appendMessage('user', text);
            
            loading.style.display = 'block';
            btn.disabled = true;
            
            try {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: text })
                });
                const data = await res.json();
                appendMessage('bot', data.answer);
            } catch (err) {
                appendMessage('bot', 'Error: Failed to connect to server.');
            } finally {
                loading.style.display = 'none';
                btn.disabled = false;
                input.focus();
            }
        }

        btn.addEventListener('click', sendMessage);
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    question = data.get("message", "")
    if not question:
        return jsonify({"answer": "Empty message."}), 400
    
    answer = rag_chain.invoke(question)
    return jsonify({"answer": answer.strip()})

@app.route("/logo.png")
def serve_logo():
    if os.path.exists("logo.png"):
        return send_from_directory(".", "logo.png")
    return "Not Found", 404

if __name__ == "__main__":
    print("Starting minimal RAG Flask application...")
    app.run(host="127.0.0.1", port=5000, debug=False)
