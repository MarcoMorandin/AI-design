import json
import copy
import inspect

import json
from google import genai
import re
from typing import List

from pydantic import BaseModel
from typing_extensions import Literal
from typing import Union, Callable, List, Optional
from tool.tool import Tool
from tool.tool_manager import ToolManager


def pretty_print_messages(messages) -> None:
    for message in messages:
        if message["role"] != "assistant":
            continue

        # print agent name in blue
        print(f"\033[94m{message['sender']}\033[0m:", end=" ")

        # print response, if any
        if message["content"]:
            print(message["content"])

        # print tool calls in purple, if any
        tool_calls = message.get("tool_calls") or []
        if len(tool_calls) > 1:
            print()
        for tool_call in tool_calls:
            f = tool_call["function"]
            name, args = f["name"], f["arguments"]
            arg_str = json.dumps(json.loads(args)).replace(":", "=")
            print(f"\033[95m{name}\033[0m({arg_str[1:-1]})")


#function tool that agent can call: no input, but return Union[str, "Agent", dict]
#it is used the forward refernce:  use a string literal to declare a name that hasn't 
# been defined yet in the code. The annotation is stored as just the name and the 
# reference to the object is resolved later.
AgentFunction = Callable[[], Union[str, "Agent", dict]]

class Agent(BaseModel):
    # Just a simple class. Doesn't contain any methods out of the box
    name: str = "Agent"
    #api_key:str="AIzaSyBSrT4FjRJB9l7Itgk1DqyJeyQ3Gm4eNNE"
    model: str = "gemini-2.0-flash"
    # could de a string or a function the return a string
    instructions: Union[str, Callable[[], str]] = "You are an agent that do sum"

    tool_manager: ToolManager = None

    class Config:
        arbitrary_types_allowed = True

    #functions: List[AgentFunction] = []
    #tool_choice: str = None
    #parallel_tool_calls: bool = True

class Response(BaseModel):
    # Response is used to encapsulate the entire conversation output
    messages: List = []
    agent: Optional[Agent] = None
    
class Function(BaseModel):
    #model the info related to the AgentFunction

    #argomenti in JSON format (see function_to_json)
    arguments: str
    name: str

class ChatCompletionMessageToolCall(BaseModel):
    #AgentFunction call during the chat

    id: str # The ID of the tool call
    function: Function # The function that the model called
    type: Literal["function"] # The type of the tool. Currently, only `function` is supported

class Result(BaseModel):
    # Result is used to encapsulate the return value of a single function/tool call
    value: str = "" # The result value as a string.
    agent: Optional[Agent] = None # The agent instance, if applicable.


class Swarm:
    # Implements the core logic of orchestrating a single/multi-agent system
    def __init__(
        self,
        client=None,
    ):
        if not client:
           client = genai.Client(api_key="AIzaSyBSrT4FjRJB9l7Itgk1DqyJeyQ3Gm4eNNE")
        self.client = client
        
    def get_chat_completion(
        self,
        agent: Agent,
        history: List,
        model_override: str
    ):
        #tools = [function_to_json(f) for f in agent.functions]
        tools=agent.tool_manager.list_tools()
        tools_info=[tool.get_tool_info() for tool in tools]

        
        system_prompt = (
            f"{agent.instructions}\n\n"
            f"Available tools:\n{tools_info}\n\n"
            "If you need to use a tool, respond in the following format:\n"
            "REASONING: [your reasoning for choosing this tool]\n"
            "TOOL: [tool_name]\n"
            "PARAMETERS: [JSON formatted parameters for the tool]\n"
            "If you don't need to use a tool, just respond normally."
        )

        conversation = [system_prompt]
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            conversation.append(f"{role.capitalize()}: {content}")

        prompt = "\n".join(conversation)

        model_name = model_override or agent.model
        
        # Call Gemini
        response = self.client.models.generate_content(
            model=model_name,
            contents=[prompt]
        )

        # Extract the assistant’s reply
        assistant_msg = response.text

        # Parse out any TOOL/PARAMETERS instructions
        tool_info = self._parse_tool_selection(assistant_msg)

        return response, tool_info
            
    def _parse_tool_selection(self, content: str):
        """Extract tool selection information from the response text."""
        if "TOOL:" in content:
            try:
                reasoning_match = re.search(r"REASONING:(.*?)(?=TOOL:|$)", content, re.DOTALL)
                tool_match      = re.search(r"TOOL:(.*?)(?=PARAMETERS:|$)", content, re.DOTALL)
                params_match    = re.search(r"PARAMETERS:(.*?)$", content, re.DOTALL)

                if tool_match:
                    tool_name  = tool_match.group(1).strip()
                    reasoning  = reasoning_match.group(1).strip() if reasoning_match else ""
                    params_str = params_match.group(1).strip() if params_match else "{}"

                    try:
                        parameters = json.loads(params_str)
                    except json.JSONDecodeError:
                        parameters = {}

                    return {
                        "tool": tool_name,
                        "reasoning": reasoning,
                        "parameters": parameters
                    }
            except Exception as e:
                print(f"Error parsing tool selection: {e}")
        return None

    def handle_function_result(self, result) -> Result:
        match result:
            case Result() as result:
                return result
            case Agent() as agent:
                return Result(
                    value=json.dumps({"assistant": agent.name}),
                    agent=agent
                )
            case _:
                try:
                    return Result(value=str(result))
                except Exception as e:
                    raise TypeError(e)


    async def handle_tool_calls(self, agent:Agent, tool_name, parameter) -> Response:
        raw_result = await agent.tool_manager.call_tool(tool_name, parameter)
        print(f'Called function {tool_name} with args: {parameter} and obtained result: {raw_result}')
        print('#############################################')
        partial_response = Response(messages=[], agent=None)
        result: Result = self.handle_function_result(raw_result)
        partial_response.messages.append(
            {
                "role": "tool",
                "tool_name": tool_name,
                "content": result.value,
            }
        )
        if result.agent:
                partial_response.agent = result.agent

        return partial_response

    
    async def run(
        self,
        agent: Agent,
        messages: List,
        model_override: str = None,
        max_turns: int = float("inf"),
        execute_tools: bool = True,
    ) -> Response:
        active_agent = agent
        history = copy.deepcopy(messages)
        init_len = len(messages)

        print('#############################################')
        print(f'history: {history}')
        print('#############################################')
        while len(history) - init_len < max_turns and active_agent:
            message, tool_info = self.get_chat_completion(
                agent=active_agent,
                history=history,
                model_override=model_override
            )

            assistant_message = {
                "role": "assistant",
                "sender": active_agent.name,
                "content": message.text
            }
            print(f'Active agent: {active_agent.name}')
            print(f"message: {assistant_message}")
            print('#############################################')
            
            
            history.append(assistant_message)

            if tool_info is None:
                print('No tool calls hence breaking')
                print('#############################################')
                break
            
            partial_response = await self.handle_tool_calls(agent, tool_info["tool"], tool_info["parameters"])
            history.extend(partial_response.messages)
            
            if partial_response.agent:
                active_agent = partial_response.agent
                message.sender = active_agent.name
        return Response(
            messages=history[init_len:],
            agent=active_agent,
        )
