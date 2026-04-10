## Show Obsidian notes and files examples under ./knowledge_sources

## Show RAD image management
python test_rag.py "Who owns the lab servers?"
python test_rag.py "Adam Kmet owns any lab devices?"

# Force reprocess all images
python preprocess_images.py --force

# Remove all cached descriptions
python preprocess_images.py --clean

# PROMPTS:
Is Adam Kmet owner of any lab device?                       ->> should use searchKnowledge
How many routers does acmeco lab have?                      ->> confuses containerlab with knowledge_source
How many routers does acmeco lab have? ignore containerlab  ->> 

## Show bogus "cisco best practices" in Obsidian and force LLM to implement
