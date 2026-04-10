import json
import time
from tools import getCurrentDateAndTime, getContainerLabTopologyInformation, getContainerLabDeviceConfiguration, executeCommandsOnContainerLabDevice, retrieveKnowledge, searchKnowledgeFiles, readKnowledgeFile, tools_definition
from helpers import debug_print, tool_call_print, tool_result_print, llm_print, info_print, Colors
from llm_client import chat_completion


def parse_arguments(arguments_raw):
    """
    Safely parse arguments which may come as a JSON string or as a dictionary.
    Returns a dictionary, or an empty dict if parsing fails.
    """
    if isinstance(arguments_raw, dict):
        return arguments_raw
    
    if isinstance(arguments_raw, str):
        try:
            return json.loads(arguments_raw)
        except json.JSONDecodeError as e:
            print(f"WARNING: Failed to parse arguments as JSON: {e}")
            print(f"         Raw arguments: {arguments_raw}")
            return {}
    
    # If it's neither dict nor string, return empty dict
    print(f"WARNING: Arguments is neither dict nor string: {type(arguments_raw)}")
    return {}


def process_tool_calls(resp, messages, tools, max_completion_tokens=1024):
    """
    Process `tool_calls` (array) 
    """
    processed_tool = False

    try:

        # Try array-style tool_calls first
        tool_calls = None
        try:
            tool_calls = resp.choices[0].message.get("tool_calls")
        except Exception:
            tool_calls = getattr(resp.choices[0].message, "tool_calls", None)

        if tool_calls and isinstance(tool_calls, (list, tuple)) and len(tool_calls) > 0:     

            # Execute each declared tool and append tool messages
            tool_calls_index = 0
            for tc in tool_calls:
                tool_calls_index += 1
                debug_print("-- tool_calls[",tool_calls_index,"]:\n", tc)

                try:
                    id = tc.get("id") if isinstance(tc, dict) else getattr(tc, "id", None)
                    function_object = tc.get("function") if isinstance(tc, dict) else getattr(tc, "function", None)
                    name = function_object.get("name") if isinstance(tc, dict) else getattr(function_object, "name", None)

                except Exception as e:
                    debug_print("Failed to parse tool_call entry:", e)
                    continue

                arguments_raw = (function_object.get("arguments") if isinstance(function_object, dict) else getattr(function_object, "arguments", {})) or {}
                arguments_object = parse_arguments(arguments_raw)

                if name == "getCurrentDateAndTime":
                    fmt = arguments_object.get("fmt", "%Y-%m-%d %H:%M:%S")
                    tool_call_print(name, {"fmt": fmt})
                    try:
                        tool_result = getCurrentDateAndTime(fmt)
                    except Exception as e:
                        tool_result = f"Error running tool: {e}"
                elif name == "getContainerLabTopologyInformation":
                    tool_call_print(name, {})
                    try:
                        tool_result = getContainerLabTopologyInformation()
                    except Exception as e:
                        tool_result = f"Error running tool: {e}"
                elif name == "getContainerLabDeviceConfiguration":
                    target = arguments_object.get("target", None)
                    tool_call_print(name, {"target": target})
                    try:
                        tool_result = getContainerLabDeviceConfiguration(target)
                    except Exception as e:
                        tool_result = f"Error running tool: {e}"
                elif name == "executeCommandsOnContainerLabDevice":
                    target = arguments_object.get("target", None)
                    commands = arguments_object.get("commands", None)
                    expected_string = arguments_object.get("expected_string", None)
                    tool_call_print(name, {"target": target, "commands": commands, "expected_string": expected_string})
                    try:
                        tool_result = executeCommandsOnContainerLabDevice(target, commands, expected_string)
                    except Exception as e:
                        tool_result = f"Error running tool: {e}"
                elif name == "retrieveKnowledge":
                    query = arguments_object.get("query", "")
                    top_k = arguments_object.get("top_k", 5)
                    tool_call_print(name, {"query": query, "top_k": top_k})
                    try:
                        tool_result = retrieveKnowledge(query, top_k)
                    except Exception as e:
                        tool_result = f"Error retrieving knowledge: {e}"
                elif name == "searchKnowledgeFiles":
                    keyword = arguments_object.get("keyword", "")
                    tool_call_print(name, {"keyword": keyword})
                    try:
                        tool_result = searchKnowledgeFiles(keyword)
                    except Exception as e:
                        tool_result = f"Error searching knowledge files: {e}"
                elif name == "readKnowledgeFile":
                    file_path = arguments_object.get("file_path", "")
                    tool_call_print(name, {"file_path": file_path})
                    try:
                        tool_result = readKnowledgeFile(file_path)
                    except Exception as e:
                        tool_result = f"Error reading knowledge file: {e}"
                else:
                    tool_result = f"Unknown tool: {name}"

                tool_result_print(name, str(tool_result))
                debug_print("DEBUG: Full tool result =", tool_result)

                tool_call_id = tc.get("id") if isinstance(tc, dict) else getattr(tc, "id", None)
                messages.append({"role": "tool", "name": name, "content": tool_result, "tool_call_id": tool_call_id})
                debug_print("   ", messages)            

            # Request a follow-up now that all tools executed
            try:
                follow = chat_completion(
                    messages=messages,
                    tools=tools,
                    max_tokens=max_completion_tokens,
                )
                debug_print("DEBUG of what we recieved from GPT (follow-up): ", follow)
                
                # Append the assistant's response (which may contain tool_calls or content)
                assistant_msg = {"role": "assistant"}
                if follow.choices[0].message.content:
                    assistant_msg["content"] = follow.choices[0].message.content.strip()
                    llm_print(assistant_msg["content"])

                # Check if the follow-up response contains tool_calls
                follow_tool_calls = getattr(follow.choices[0].message, "tool_calls", None)
                if follow_tool_calls:
                    assistant_msg["tool_calls"] = follow_tool_calls

                messages.append(assistant_msg)

                try:
                    info_print("Tokens:", f"prompt={follow.usage.prompt_tokens}  completion={follow.usage.completion_tokens}  total={follow.usage.total_tokens}")
                except Exception:
                    pass

                # If follow-up contains tool calls, process them recursively
                if follow_tool_calls:
                    debug_print("Follow-up response contains tool_calls, processing recursively...")
                    messages, tool_processed = process_tool_calls(follow, messages, tools, max_completion_tokens)
                    return messages, tool_processed
                    
            except Exception as e:
                print(f"{Colors.RED}API error during follow-up:{Colors.RESET}", e)
                time.sleep(1)

            processed_tool = True
            return messages, True

    except Exception as e:
        print(f"{Colors.RED}Tool processing error:{Colors.RESET}", e)

    return messages, processed_tool
