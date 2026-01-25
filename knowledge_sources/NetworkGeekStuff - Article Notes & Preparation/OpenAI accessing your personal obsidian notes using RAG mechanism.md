# How to Make ChatGPT Access Your Personal Obsidian Notes Using RAG

Have you ever wished ChatGPT could answer questions about YOUR personal notes? Like "What are my lab credentials?" or "Who do I contact for hardware purchases?" - things only you would know from your private documentation?

In this article, I'll show you how to build a simple RAG (Retrieval-Augmented Generation) system that lets you chat with OpenAI while it seamlessly pulls context from your local Obsidian notes when needed.

## What We're Building

We're creating an AI assistant that:
- Chats normally with you using OpenAI's GPT models
- Automatically detects when a question might relate to your personal notes
- Retrieves relevant information from your local knowledge base
- Combines AI intelligence with YOUR specific documentation

The best part? Your notes stay local - only relevant snippets are sent to the AI when needed.

---

## Getting Started

### Step 1: Clone the Repository

```bash
git clone https://github.com/zerxen/AI_NetworkGeekStuff_Assistant
cd AI_NetworkGeekStuff_Assistant
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Configure Your API Key

Copy the template and add your OpenAI API key:

```bash
cp config.py_template config.py
```

Edit `config.py` and replace the placeholder with your actual key:

```python
OPENAI_API_KEY = "sk-your-actual-api-key-here"
MODEL = "gpt-4o-mini"
```

You can get an API key from [OpenAI Platform](https://platform.openai.com/account/api-keys). Note that API usage requires a paid account (minimum $5 credit).

---

## Understanding the Knowledge Sources

The project includes example knowledge sources in the `knowledge_sources/` directory. Let's look at what's there:

### Example 1: Company Contacts (acmeco/contacts/)

```markdown
# ACME Co Internal Contacts

## Procurement Department

| Name | Role | Email | Phone | Notes |
|------|------|-------|-------|-------|
| Sarah Mitchell | Procurement Manager | s.mitchell@acmeco.com | ext. 2401 | Approves orders over $5000 |
| Dave Chen | Hardware Buyer | d.chen@acmeco.com | ext. 2405 | Contact for network equipment |

## IT / Network Team (Colleagues)

| Name | Role | Email | Phone | Notes |
|------|------|-------|-------|-------|
| Tom Bradley | Network Architect | t.bradley@acmeco.com | ext. 4501 | Senior, 10+ years |
| Rachel Kim | Security Analyst | r.kim@acmeco.com | ext. 4520 | Firewall changes need her approval |
```

### Example 2: Lab Credentials (acmeco/lab_documentation/)

```markdown
# Lab Device Credentials

> Note: These are LAB credentials only.

## Network Devices (Cisco)

**Standard Lab Login**:
- Username: `labadmin`
- Password: `LabTest123!`
- Enable: `EnableLab!`

**Applies to**: Lab-FW-01, Lab-SW-01, Lab-SW-02, R1, R2, R3
```

### Example 3: Personal Recipes (Recipes/)

Yes, even your cooking notes work! The system indexes everything in markdown format:

```markdown
**Quick Omelette Recipe (1 serving)**

**Ingredients**
- 2-3 eggs
- Salt and black pepper
- 1 tbsp butter or oil

**Steps**
1. Crack the eggs into a bowl, add a pinch of salt and pepper...
```

---

## Testing the RAG System

Before chatting, let's verify the RAG pipeline works. The project includes `test_rag.py` for this purpose.

### Running the Test

```bash
python test_rag.py
```

You'll see output like this:

```
============================================================
Testing RAG Pipeline Initialization
============================================================

1. Initializing RAG Manager...
RAG Manager created (vector store will be initialized on first query)
   Clearing database as requested...
Vector store cleared

2. Testing document retrieval...
   Query 1: 'cisco lab credentials'
   Retrieved relevant documents
   Preview: ## Relevant Knowledge from Sources:

**[1] From lab_credentials.md:**
# Lab Device Credentials > Note: These are LAB credentials only...
```

### Customizing Test Queries

Want to test different queries? Edit line 38 in `test_rag.py`:

```python
test_queries = [
    "cisco lab credentials",
    "who handles procurement",
    "omelette recipe"
]
```

Each query will search your knowledge base and return relevant matches.

---

## How Vectorization Works (The Magic Behind RAG)

Here's where it gets interesting. How does the system know that "cisco lab credentials" should return your credentials file?

### Text to Numbers

When you run the system, your markdown files are converted into **embedding vectors** - arrays of numbers that represent the semantic meaning of the text. OpenAI's `text-embedding-3-small` model does this conversion.

For example, conceptually:

```
"Lab Device Credentials - Cisco - Username: labadmin"
    -> [0.023, -0.156, 0.891, 0.044, ... ] (1536 dimensions)

"Network Devices - Password: LabTest123!"
    -> [0.019, -0.148, 0.887, 0.051, ... ] (similar vector)

"Quick Omelette Recipe - eggs, butter"
    -> [-0.234, 0.567, 0.123, -0.445, ... ] (very different vector)
```

### Similarity Search

When you query "cisco lab credentials":
1. Your query is converted to a vector: `[0.021, -0.152, 0.889, ...]`
2. ChromaDB finds vectors that are mathematically "close" to yours
3. The credentials document has a similar vector -> it's returned as relevant
4. The recipe has a very different vector -> it's ignored

This is called **cosine similarity** - measuring the angle between vectors. Similar meaning = similar direction = small angle = high similarity.

### Local Storage

All embeddings are stored locally in the `chroma_db/` folder. Your notes never leave your machine until you actually ask a question that needs them.

---

## Chatting with the AI Assistant

Now for the main event - let's chat with the AI while it uses your knowledge base.

### Starting the Chat

```bash
python main.py
```

```
Initializing RAG knowledge base...
Knowledge base ready.

Interactive ChatGPT CLI (type 'exit' or Ctrl-C to quit)
You:
```

### Example Conversation

**You:** What are the lab credentials for Cisco devices?

The AI recognizes this might need local knowledge and calls the `retrieveKnowledge` tool:

```
Tool executed called: retrieveKnowledge with query='cisco lab credentials' top_k=5
.. results of tool call provided to the context

ChatGPT (after tools): Based on your lab documentation, the Cisco device
credentials are:

- Username: labadmin
- Password: LabTest123!
- Enable password: EnableLab!

These apply to Lab-FW-01, Lab-SW-01, Lab-SW-02, R1, R2, and R3.
```

**You:** Who should I contact about buying new network switches?

```
ChatGPT (after tools): For network equipment purchases, you should contact
Dave Chen (Hardware Buyer) at d.chen@acmeco.com, extension 2405.

For orders over $5000, you'll also need approval from Sarah Mitchell
(Procurement Manager) at extension 2401.
```

**You:** How do I make an omelette?

```
ChatGPT (after tools): Here's the quick omelette recipe from your notes:

1. Crack 2-3 eggs into a bowl, add salt and pepper, whisk briefly
2. Heat butter in a non-stick pan over medium heat
3. Pour in eggs, swirl to spread evenly
4. Add fillings to one half when edges set (30-60 seconds)
5. Fold in half, cook another 30-60 seconds
6. Serve immediately!
```

### How It Decides When to Use RAG

The magic happens in the system prompt. The AI is instructed:

> "Use the 'retrieveKnowledge' tool whenever you need to reference specific documentation, technical details, or look up configuration examples. Only use it when necessary - avoid overusing it for general knowledge."

So if you ask "What is BGP?" - it answers from general knowledge. But "What's MY lab's BGP configuration?" triggers a knowledge retrieval.

---

## Setting Up Your Own Knowledge Base

Replace the example files with your actual notes:

1. Delete the example folders in `knowledge_sources/`
2. Copy your Obsidian vault (or any markdown files) into `knowledge_sources/`
3. Run `python test_rag.py` to rebuild the database

The system will automatically:
- Scan all `.md` files recursively
- Split them into intelligent chunks (respecting markdown structure)
- Generate embeddings and store them locally

---

## A Personal Note

The example data in this project (the "acmeco" company) is actually a sanitized version of my real Obsidian vault. I've been using this system to help me:

- **Find old meeting notes** - "What did we discuss in the January network planning meeting?"
- **Look up contacts** - "Who handles software licensing again?"
- **Remember lab details** - "What's the management IP for the firewall?"

After years of accumulating notes, it became impossible to remember where everything was. Now I just ask the AI, and it finds the relevant note for me - like having a personal assistant who has read everything I've ever written.

---

## Conclusion

RAG bridges the gap between powerful AI models and your personal knowledge. The AI provides intelligence and natural conversation; your notes provide the specific, private information only you have.

The complete code is available at: **https://github.com/zerxen/AI_NetworkGeekStuff_Assistant**

Give it a try with your own Obsidian vault - you might be surprised how useful it is to finally have an AI that actually knows YOUR stuff.

---

*Have questions or improvements? Open an issue on GitHub or drop a comment below!*
