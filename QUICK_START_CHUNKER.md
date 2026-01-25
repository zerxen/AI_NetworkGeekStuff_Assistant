# Quick Start: Testing the New Intelligent Chunker

## Overview

The intelligent markdown chunker is now fully integrated. Here's how to test it:

---

## Option 1: Quick Test (Recommended for First Run)

```bash
python test_chunker.py
```

This runs a sample test with a small markdown document and shows:
- Chunking output with logging
- Generated chunks and their metadata
- Summary statistics

---

## Option 2: Full RAG System Test

Enable debug output and run the main assistant:

1. **Enable DEBUG_MODE in config.py:**
   ```python
   DEBUG_MODE = True
   ```

2. **Start the assistant:**
   ```bash
   python main.py
   ```

3. **Observe the output:**
   - You'll see detailed chunking progress as RAG initializes
   - Per-file chunking stats
   - Session summary with directory contexts
   - Then the interactive chat prompt

---

## Option 3: Rebuild RAG Database

If you have an existing Chroma database, rebuild it with the new chunker:

```python
from rag_manager import get_rag_manager

rag = get_rag_manager()
rag.rebuild_database()  # Clears and rebuilds with new chunker
```

---

## What to Look For

### Per-File Output
```
[CHUNKING] Processing: "filename.md" from directory: "Category"
  |-- Extracted headings: 1 H1, 3 H2, 5 H3 sections
  |-- Generated chunks: 4 chunks (avg 2.1KB per chunk)
  |-- Directory context: "Category" -> All chunks enriched
  `-- Summary: Directory + heading hierarchy applied to 4 chunks
```

**Check:**
- ✅ Headings extracted correctly
- ✅ Chunk count makes sense for file size
- ✅ Directory context shown
- ✅ Average chunk size in expected range (500-8000 chars)

### Session Summary
```
[CHUNKING] Summary:
  |-- Total files processed: 42
  |-- Total chunks generated: 287
  |-- Average chunk size: 2847 chars
  |-- Directory contexts applied: 12 unique directories
  `-- Enrichment stats: 100% chunks have directory context
```

**Check:**
- ✅ Reasonable chunk count (more than naive, but not excessive)
- ✅ Average size in ideal range (~2000-4000 chars is good)
- ✅ Multiple directories detected
- ✅ 100% enrichment (all chunks have context)

---

## Configuration

### Tune Chunk Sizes in config.py

```python
# Conservative: Larger chunks, fewer total
CHUNK_MIN_SIZE = 800
CHUNK_IDEAL_SIZE = 4000
CHUNK_MAX_SIZE = 10000

# Aggressive: Smaller chunks, more total  
CHUNK_MIN_SIZE = 300
CHUNK_IDEAL_SIZE = 2000
CHUNK_MAX_SIZE = 5000

# Balanced (Default)
CHUNK_MIN_SIZE = 500
CHUNK_IDEAL_SIZE = 3000
CHUNK_MAX_SIZE = 8000
```

### Toggle Debug Output

```python
# Show detailed chunking progress
DEBUG_MODE = True

# Disable for production/quiet operation
DEBUG_MODE = False
```

---

## Troubleshooting

### Issue: Very small chunks
**Cause:** `CHUNK_MIN_SIZE` too small or many small sections in markdown  
**Solution:** Increase `CHUNK_MIN_SIZE` to 1000-1500

### Issue: Very large chunks
**Cause:** `CHUNK_MAX_SIZE` too large or few heading subdivisions  
**Solution:** Decrease `CHUNK_MAX_SIZE` to 5000-6000

### Issue: Not enough chunks
**Cause:** `CHUNK_IDEAL_SIZE` too large  
**Solution:** Decrease to 2000 chars

### Issue: Too many chunks
**Cause:** `CHUNK_MIN_SIZE` too low or fine-grained heading structure  
**Solution:** Increase `CHUNK_MIN_SIZE` to filter tiny chunks

### Issue: Directory context not appearing
**Cause:** Knowledge source directory structure might be flat  
**Solution:** Check `KNOWLEDGE_SOURCES_PATH` contains subdirectories

---

## Expected Results

For a typical Obsidian vault with:
- **Input:** ~40-50 markdown files
- **Result:** ~250-350 chunks
- **Average size:** 2500-3500 chars
- **Coverage:** 100% of knowledge base with context

Compared to old chunker (naive):
- **Old:** ~500-600 arbitrary chunks, no context
- **New:** ~250-350 semantic chunks, full context

**Quality:**
- Better embedding vectors (more semantic)
- Better retrieval accuracy (context preserved)
- Better reader understanding (full hierarchy in metadata)

---

## Files to Monitor

After enabling DEBUG_MODE, check:

1. **Console output during init:**
   - Chunking progress (per-file)
   - Session summary
   - Total time to initialize

2. **RAG quality:**
   - Ask knowledge-specific questions
   - Check if retrieved content is relevant
   - Verify heading context in results

3. **Performance:**
   - Initial load time with `rebuild_database()`
   - Query latency (should be similar to before)
   - Memory usage (might be slightly different)

---

## Next Steps

1. ✅ Run `test_chunker.py` for quick validation
2. ✅ Enable `DEBUG_MODE` and start `main.py`
3. ✅ Observe the chunking output
4. ✅ Test with real Obsidian vault
5. ⏳ Tune chunk size parameters if needed
6. ⏳ Run full RAG tests and validate quality

---

## Key Files Modified

- `markdown_chunker.py` - NEW: Intelligent chunking engine
- `knowledge_loader.py` - Updated to pass directory context
- `rag_manager.py` - Updated to use new chunker
- `config.py` - Added chunking parameters
- `test_chunker.py` - Sample test script

---

## Support

For issues or questions:
1. Check [PHASE1_IMPLEMENTATION_COMPLETE.md](PHASE1_IMPLEMENTATION_COMPLETE.md) for detailed implementation info
2. Check [CHUNK_OPTIMIZATION_DESIGN.md](CHUNK_OPTIMIZATION_DESIGN.md) for design rationale
3. Check [CHUNKING_LOGGING_SPEC.md](CHUNKING_LOGGING_SPEC.md) for logging format details

