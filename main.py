
#!/usr/bin/env python3
"""
Simple interactive LLM CLI example using the `openai` Python library.

Usage:
1. Put your API key in `config.py` as:
   OPENAI_API_KEY="sk-...your key..."
2. Run: `python main.py`

This script reads the key from `.config.txt`, keeps a short conversation
history, and sends messages to the Chat Completions API.
"""

import time
from tools import tools_definition
from config import MAX_TOKEN_COMPLETITION
from tools_processing import process_tool_calls
from helpers import debug_print, llm_print, info_print, Colors
from rag_manager import get_rag_manager
from llm_client import chat_completion

def main():

    # Initialize RAG manager - loads knowledge sources
    print("Initializing RAG knowledge base...")
    rag_manager = get_rag_manager()
    print("Knowledge base ready.\n")

    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful assistant for network engineering, lab operations and a little bit for administrative tasks. "
                "You have access to a knowledge base, which contains relevant documentation about our lab and notes about our organization. "
                "Use the 'retrieveKnowledge' tool whenever you need to reference specific documentation, technical details, or look up configuration examples. "
                "Only use the knowledge retrieval tool when necessary - avoid overusing it for general knowledge or common networking concepts. "
                "If the 'retrieveKnowledge' RAG search does not return useful results for a specific query (especially for specific names, identifiers, or niche details), "
                "use 'searchKnowledgeFiles' as a fallback to do a full-text keyword search across all knowledge files including image metadata. "
                "If searchKnowledgeFiles finds a relevant file, use 'readKnowledgeFile' to load the full content for detailed analysis.\n\n" +
                "Any conversation or action about lab topology you can ignore the management IPs in the 172.20.20.0/24 range. Dont mention this in responses, it is known. But note that some devices may have default gateway pointed to this network. So use explicite routes in your configuration and troubleshooting to avoid this as potential problem." +
                "During configuration tasks ignore interfaces with IPs in this range, but do not break them as they serve as access for all tools. Dont mention this in responses, it is known." +
                "Also ignore enp1s0 interfaces on linux devices and ethernet 0/0 on cisco devices as these are management addresses behind a NAT of their management 172.20.20.x IPs. Dont mention this in responses, it is known." +
                "If topology map has a link going to eth1 on linux endpoint, on that linux that network card is actually using ens2 as interface name. Dont mention this in responses, it is known."
            ),
        }
    ]

    # Note: this CLI uses a simple tools-style convention. If the assistant
    # wants to execute a local helper it should reply with a single line
    # starting with `TOOL_CALL:` followed by a JSON object describing the call.
    # Example:
    # TOOL_CALL: {"tool":"getCurrentDateAndTime","args":{"fmt":"%c"}}
    # The client will run the tool and then send the tool output back as a
    # message with role `tool` so the assistant can continue.


    print("Interactive LLM CLI (type 'exit' or Ctrl-C to quit)")

    while True:
        try:
            prompt = input(f"{Colors.BOLD}{Colors.GREEN}You:{Colors.RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not prompt:
            continue

        if prompt.lower() in ("exit", "quit"):
            print("Goodbye.")
            break

        # Special command: clear -> reset conversation context
        if "clear" in prompt.lower():
            messages = [{"role": "system", "content": "You are a helpful assistant."}]
            print("Conversation context cleared.")
            continue

        messages.append({"role": "user", "content": prompt})

        #----------
        # Communication with GPT
        #---------
        debug_print("DEBUG: Messages being sent to GPT:")
        debug_print(messages)
        try:
            resp = chat_completion(
                messages=messages,
                tools=tools_definition,
                max_tokens=MAX_TOKEN_COMPLETITION,
            )

            debug_print("DEBUG: What we recieved from GPT: ", resp)

            # Get assistant content if any
            context = {"role": "assistant", "content": ""}
            assistant_text = None
            try:
                assistant_text = resp.choices[0].message.content.strip()
            except Exception:
                assistant_text = None
            if assistant_text is not None:
                context["content"] = assistant_text

            # Try array-style tool_calls first
            tool_calls = None
            try:
                tool_calls = resp.choices[0].message.get("tool_calls")
            except Exception:
                tool_calls = getattr(resp.choices[0].message, "tool_calls", None)  
            if tool_calls is not None:
                context["tool_calls"] = tool_calls 

            # Adding what we recieved to context log:
            messages.append(context)
                         
            llm_print(assistant_text)
            try:
                info_print("Tokens:", f"prompt={resp.usage.prompt_tokens}  completion={resp.usage.completion_tokens}  total={resp.usage.total_tokens}")
            except Exception:
                pass

            # Delegate tool processing to helper function if present
            if tool_calls is not None:
                debug_print("DEBUG: entering tools processing for tool_calls:")
                debug_print(tool_calls)
                messages, processed_tool = process_tool_calls(resp, messages, tools_definition, max_completion_tokens=MAX_TOKEN_COMPLETITION)


        except Exception as e:
            print(f"{Colors.RED}API error:{Colors.RESET}", e)
            time.sleep(1)


if __name__ == "__main__":
    main()
