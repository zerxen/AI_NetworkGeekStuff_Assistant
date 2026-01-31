# Teaching Your AI Assistant to See - Extending RAG with Image Understanding

In the previous article, we built a RAG-powered AI assistant that can answer questions from your personal Obsidian notes. It works great for text - but what about all those network diagrams, topology maps, and screenshots scattered across your documentation?

If you're anything like me, your notes are full of images. Network topologies drawn in draw.io, screenshots of configurations, Visio diagrams of data center layouts. The problem? Our RAG system was completely blind to them. When the AI searched your knowledge base, it only saw the markdown text around the image link - not what the image actually contained.

In this article, I'll show you how we solved that by teaching the AI to "see" images before they ever enter the RAG pipeline.

---

## The Problem: Invisible Images

Let's look at a concrete example. In our ACME Co lab documentation, there's a network topology document that contains this markdown:

```markdown
## Lab Network Topology
![[images\lab_topology.png]]

## Device Inventory
| Hostname | Model                        | Management IP | Purpose            |
| -------- | ---------------------------- | ------------- | ------------------ |
| Cisco1   | Cisco 2610 router            | 172.16.1.1    | Router for testing |
| Cisco2   | Cisco 2610 router            | 172.16.2.1    | Router for testing |
| Ubuntu1  | Virtual Machine on ESX1 host | 172.16.1.10   | Linux VM           |
| Ubuntu2  | Virtual Machine on ESX2 host | 172.16.1.11   | Linux VM           |
```

The topology image shows the full network diagram with IP addresses, interface names, and - importantly - a note that "Adam Kmet owns ubuntu2 server." But when someone asks the AI "Who owns the ubuntu2 server?", the RAG system has no idea. It only indexed the text, and the text says nothing about ownership. That information exists only inside the PNG file.

We needed a way to extract the knowledge locked inside images and feed it into the RAG pipeline.

---

## The Solution: Image Preprocessing with Vision LLM

The approach is straightforward: before the RAG system indexes your documents, we run every image through a vision-capable LLM that generates a detailed text description. This description is saved as a sidecar metadata file next to the original image. Later, when the markdown chunker processes documents for RAG, it finds image links, looks up the corresponding description, and injects it directly into the text chunk.

Here's the flow:

```
Image files in knowledge base
    |
    v
preprocess_images.py  (Vision LLM describes each image)
    |
    v
Sidecar .meta.json files  (Text descriptions stored alongside images)
    |
    v
RAG chunking  (Descriptions injected into markdown chunks)
    |
    v
Vector database  (Images now searchable as text)
```

The beauty of this approach is that the image descriptions become part of the regular text chunks. No special image search needed - the standard RAG similarity search handles everything.

---

## Step 1: Preprocessing Images

### Running the Preprocessor

The entry point is `preprocess_images.py`. It scans your entire knowledge base for image files, sends each one to a vision LLM, and saves the description.

```bash
# Process new or modified images
python preprocess_images.py

# Force reprocess all images (e.g., after changing the vision model)
python preprocess_images.py --force

# Clean all cached descriptions
python preprocess_images.py --clean
```

When you run it, you'll see output like this:

```
============================================================
Image Preprocessor for RAG
============================================================
Image Preprocessor initialized: provider=local, model=mistralai/devstral-small-2-2512

Processing new/modified images...
Found 1 images in knowledge base
  Processing: lab_topology.png

Completed: 1 processed, 0 skipped, 0 errors
============================================================
```

### What Happens Under the Hood

The `ImagePreprocessor` class in `image_preprocessor.py` does the heavy lifting. For each image it:

1. **Scans the knowledge base** for supported image formats (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.bmp`)
2. **Checks timestamps** - only processes new or modified images (compares image modification time against the existing metadata)
3. **Encodes the image** as base64 and sends it to a vision-capable LLM
4. **Saves the result** as a `.meta.json` sidecar file right next to the original image

The prompt sent to the vision model is carefully crafted for our use case:

```python
prompt = f"""Describe this image in detail for a knowledge base search system.
Focus on:
- What the image shows (diagrams, screenshots, network topologies, photos, etc.)
- All text visible in the image
- Technical details if it's a network/system diagram
- Key elements and their relationships
- If you notice any errors or anomalies in the image
- All IP addresses, hostnames, labels, and annotations visible

Image filename: {image_path.name}

Provide a concise but comprehensive description (2-5 sentences) that would
help someone find this image when searching for related topics."""
```

Notice that the prompt specifically asks for IP addresses, hostnames, and annotations. For network documentation, these are the details people actually search for.

### Choosing a Vision Model

The preprocessor supports both OpenAI (GPT-4o) and local models via LM Studio. Configure it in `config.py`:

```python
# Vision provider: "openai" or "local"
VISION_PROVIDER = "local"

# Local model (loaded in LM Studio)
LOCAL_VISION_MODEL = "mistralai/devstral-small-2-2512"

# Image processing settings
IMAGE_MAX_SIZE_MB = 20
IMAGE_DESCRIPTION_MAX_TOKENS = 1000
```

I'm using Devstral Small running locally in LM Studio. It's a capable vision model that runs well on consumer hardware and keeps all your data private - no images sent to the cloud.

---

## Step 2: The Sidecar Metadata File

After processing, each image gets a companion `.meta.json` file. For our lab topology image `lab_topology.png`, the preprocessor creates `lab_topology.png.meta.json`:

```json
{
  "image_path": "knowledge_sources\\acmeco\\lab_documentation\\images\\lab_topology.png",
  "description": "This image depicts a linear network topology consisting of two
    Cisco routers (cisco1 and cisco2) connected between two Ubuntu servers (ubuntu1
    and ubuntu2). The diagram shows IP addressing details, with all devices assigned
    to the subnet 10.20.30.0/24. Key elements include:\n\n- ubuntu1 (ens2: 10.20.30.10)
    connected to cisco1 via E0/2.\n- cisco1 (E0/0: OOB, E0/1: 10.20.30.1) linked to
    cisco2 via E0/1.\n- cisco2 (E0/0: OOB, E0/2: 10.20.30.1) connected to ubuntu2
    via E0/2.\n- ubuntu2 (ens2: 10.20.30.10) labeled as owned by Adam Kmet.\n\n
    The topology appears correct with no visible errors, but the IP assignment for
    ubuntu2 conflicts with ubuntu1 (both using 10.20.30.10). There is note that
    Adam Kmet owns ubuntu2 server.",
  "generated_at": "2026-01-31T19:27:28.558630Z",
  "model_used": "mistralai/devstral-small-2-2512",
  "provider": "local",
  "file_size_bytes": 55643
}
```

Look at what the vision model extracted from a simple PNG diagram:

- The full network topology (ubuntu1 - cisco1 - cisco2 - ubuntu2)
- All IP addresses (10.20.30.0/24 subnet, individual IPs for each device)
- Interface names (ens2, E0/0, E0/1, E0/2)
- The ownership annotation: **"Adam Kmet owns ubuntu2 server"**
- Even caught a potential issue: both Ubuntu servers sharing the same IP

That ownership note was just a small text annotation in the corner of a draw.io diagram. A human might easily miss it when skimming, but the vision model picked it up and wrote it into searchable text.

---

## Step 3: How Descriptions Enter the RAG Pipeline

This is where the magic happens. The `ObsidianMarkdownChunker` in `markdown_chunker.py` has an image injection step that runs before any chunking occurs.

### Resolving Image Paths

First, the system needs to find the actual image file from the markdown link. Obsidian uses wiki-style links like `![[images\lab_topology.png]]`, while standard markdown uses `![alt](path.png)`. The `ImageResolver` class handles both formats and searches multiple locations:

1. Exact path relative to the markdown file
2. Same directory as the markdown file
3. `Images/` subdirectory relative to the markdown file
4. Global `Images/` in knowledge sources root
5. Recursive search as a last resort

This is important because Obsidian vaults often have images scattered across different folders, and users rarely think about path conventions when pasting screenshots.

### Injecting Descriptions

Once the image is found and its `.meta.json` sidecar exists, the chunker injects the description directly into the markdown content:

```python
def _inject_image_descriptions(self, content, markdown_path):
    resolver = ImageResolver()
    links = resolver.find_image_links(content)

    for full_match, image_ref in links:
        image_path = resolver.resolve_image_path(image_ref, markdown_path)

        if image_path is None:
            injection = "\n[IMAGE NOT FOUND: {image_ref}]"
        else:
            description = resolver.get_image_description(image_path)
            if description:
                injection = "\n[IMAGE: {image_ref} - {description}]"
            else:
                injection = "\n[IMAGE NOT PROCESSED: {image_ref} - Run preprocess_images.py]"

        result = result.replace(full_match, full_match + injection, 1)
    return result
```

So our lab overview document, which originally had just `![[images\lab_topology.png]]`, now gets chunked as if it contained:

```markdown
## Lab Network Topology
![[images\lab_topology.png]]
[IMAGE: images\lab_topology.png - This image depicts a linear network topology
consisting of two Cisco routers (cisco1 and cisco2) connected between two Ubuntu
servers (ubuntu1 and ubuntu2). The diagram shows IP addressing details, with all
devices assigned to the subnet 10.20.30.0/24... Adam Kmet owns ubuntu2 server.]
```

The image description becomes part of the text chunk. When that chunk gets embedded into the vector database, all the information from the image - IP addresses, device names, ownership notes - becomes searchable through standard RAG retrieval.

---

## Step 4: Testing It Out

Let's verify it works. The project includes `test_rag.py` with a query specifically designed to test image-based knowledge retrieval:

```python
test_queries = [
    "Adam Kmet is owner of any acmeco lab server?"
]
```

Remember: "Adam Kmet owns ubuntu2" exists nowhere in any markdown text file. This information only exists inside the topology PNG image, extracted by the vision model into the sidecar metadata.

### Running the Test

```bash
python test_rag.py
```

```
============================================================
Testing RAG Pipeline Initialization
============================================================

1. Initializing RAG Manager...
   RAG Manager initialized successfully

   Clearing database as requested...
   Database cleared

2. Testing document retrieval...

   Query 1: 'Adam Kmet is owner of any acmeco lab server?'
   Retrieved relevant documents
   Preview: ## Relevant Knowledge from Sources:

   **[1] From ACME Co Network Lab Overview.md:**
   ...ubuntu2 (ens2: 10.20.30.10) labeled as owned by Adam Kmet...
   There is note that Adam Kmet owns ubuntu2 server...
============================================================
All tests completed successfully!
============================================================
```

The RAG system found the answer - from an image.

### Testing with the Full AI Assistant

You can also test this interactively by starting a full chat session:

```bash
python main.py
```

```
You: Adam Kmet is owner of any acmeco lab server?

Tool executed called: retrieveKnowledge with query='Adam Kmet acmeco lab server owner'
.. results of tool call provided to the context

AI Assistant: Yes, based on the lab documentation, Adam Kmet is the owner of the
ubuntu2 server in the ACME Co network lab. The server is a virtual machine running
on ESX2 host with management IP 172.16.1.11, connected to the network at IP
10.20.30.10 via interface ens2.
```

The AI answered correctly - using information that was originally locked inside a PNG diagram. Without image preprocessing, this question would have gone unanswered.

---

## Side Note: When RAG Isn't Enough

There's one honest caveat with this approach. RAG uses vector similarity to rank results, and embedding models don't always prioritize small side notes the way you'd expect. If "Adam Kmet" is mentioned in one sentence buried inside a large topology description, the embedding model might not rank that chunk high enough for a top-5 retrieval - especially when your knowledge base grows larger.

For these edge cases, the project also implements two fallback tools that the LLM can use when RAG comes up empty:

- **`searchKnowledgeFiles`** - A full-text keyword search across all files in the knowledge base (including `.meta.json` sidecar files). This is the brute-force approach: if the word "Adam" appears anywhere, it will find it.
- **`readKnowledgeFile`** - Once a relevant file is found, this tool loads its full content for the LLM to analyze.

The system prompt instructs the AI to try RAG first, and if it doesn't return useful results for specific names or identifiers, fall back to keyword search:

```python
"If the 'retrieveKnowledge' RAG search does not return useful results for a
specific query (especially for specific names, identifiers, or niche details),
use 'searchKnowledgeFiles' as a fallback to do a full-text keyword search
across all knowledge files including image metadata."
```

This two-layer approach - semantic search first, exact keyword match as fallback - handles both the common case (RAG finds it) and the edge case (small detail buried in a large chunk) reliably.

---

## Wrapping Up

With image preprocessing added to the pipeline, the AI assistant can now answer questions about content that exists only in diagrams, screenshots, and topology maps. The key insight is that we don't need multimodal RAG or complex image embedding models. We just need to convert images to text once, store the descriptions as sidecar files, and let the existing text-based RAG pipeline handle the rest.

To add image understanding to your setup:

1. Make sure you have a vision-capable model available (locally via LM Studio or through OpenAI)
2. Run `python preprocess_images.py` to generate descriptions for all images
3. The RAG system automatically picks up the descriptions on the next query

The approach scales well - preprocessing happens once per image (with timestamp-based caching), and the text descriptions add minimal overhead to the chunking and embedding process.

The complete code is available at: **https://github.com/zerxen/AI_NetworkGeekStuff_Assistant**

---

*This is a continuation of the article "Making AI accessing your personal work notes using RAG mechanism to be your work assistant." If you haven't set up the base project yet, start there first!*