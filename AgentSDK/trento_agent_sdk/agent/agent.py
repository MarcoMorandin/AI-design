import json
import copy

import json
from google import genai
import re
from typing import List

from pydantic import BaseModel
from typing_extensions import Literal
from typing import Union, Callable, List, Optional
from ..tool.tool import Tool
from ..tool.tool_manager import ToolManager
import ast


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


class Agent(BaseModel):
    name: str = "Agent"
    model: str = "gemini-2.0-flash"
    instructions: Union[str, Callable[[], str]] = "You are an agent that do sum"
    tool_manager: ToolManager = None

    # since TollManager is not pydantic
    class Config:
        arbitrary_types_allowed = True


class Response(BaseModel):
    # Encapsulate the entire conversation output
    messages: List = []
    agent: Optional[Agent] = None


class Result(BaseModel):
    # Encapsulate the return value of a single function/tool call
    value: str = ""  # The result value as a string.
    agent: Optional[Agent] = None  # The agent instance, if applicable.


class Swarm:
    # Questo rappresenta l'orchestrator ma, TODO: ce ne sono di due tipi (manager e decentralized) → quando mettiamo più agenti poi vediamo come fare
    def __init__(
        self,
        client=None,
    ):
        if not client:
            client = genai.Client(api_key="AIzaSyBSrT4FjRJB9l7Itgk1DqyJeyQ3Gm4eNNE")
        self.client = client

    def get_chat_completion(self, agent: Agent, history: List, model_override: str):

        tools = agent.tool_manager.list_tools()
        tools_info = [tool.get_tool_info() for tool in tools]

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
            model=model_name, contents=[prompt]
        )

        # Extract the assistant’s reply
        assistant_msg = response.text

        # Parse out any TOOL/PARAMETERS instructions
        tool_info = self._parse_tool_selection(assistant_msg)
        print(f"TOOL INFO: {tool_info}")
        return response, tool_info

    def _parse_tool_selection(self, content: str):
        print("CONTENT")
        print("#############################################")
        print(content)
        print("#############################################")
        """Extract tool selection information from the response text."""
        if "TOOL:" in content:
            try:
                # il reasing per ora non ci serve
                # reasoning_match = re.search(r"REASONING:(.*?)(?=TOOL:|$)", content, re.DOTALL)
                tool_match = re.search(
                    r"TOOL:(.*?)(?=PARAMETERS:|$)", content, re.DOTALL
                )
                params_match = re.search(r"PARAMETERS:(.*?)$", content, re.DOTALL)

                if tool_match:
                    # reasoning  = reasoning_match.group(1).strip() if reasoning_match else ""
                    tool_name = tool_match.group(1).strip()
                    params_str = params_match.group(1).strip() if params_match else "{}"

                    try:
                        # fixed = self._escape_invalid_json_escapes(params_str)
                        print(f"PARAM_BEFORE_JSON: {params_str}\n")
                        parameters = ast.literal_eval(params_str)
                        # params_str_dumps = json.dumps(params_str)
                        # parameters = json.loads(fixed)

                        print(f"PARAMETERS: {parameters}")
                    except json.JSONDecodeError:
                        print(f"PARAMETERS: VUOTO")
                        parameters = {}

                    return {
                        "tool": tool_name,
                        # "reasoning": reasoning,
                        "parameters": parameters,
                    }
            except Exception as e:
                print(f"Error parsing tool selection: {e}")
        return None

    def handle_function_result(self, result) -> Result:
        match result:
            case Result() as result:
                return result
            case Agent() as agent:
                return Result(value=json.dumps({"assistant": agent.name}), agent=agent)
            case _:
                try:
                    return Result(value=str(result))
                except Exception as e:
                    raise TypeError(e)

    async def handle_tool_calls(self, agent: Agent, tool_name, parameter) -> Response:
        print(f"CALLED FUNCTION {tool_name} WITH ARGS: {parameter}")

        raw_result = await agent.tool_manager.call_tool(tool_name, parameter)
        print(f"AND OBTAINED RESULTs: {raw_result}")
        print("#############################################")
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
    ) -> Response:
        active_agent = agent
        history = copy.deepcopy(messages)
        init_len = len(messages)

        # print('#############################################')
        # print(f'history: {history}')
        # print('#############################################')
        while len(history) - init_len < max_turns and active_agent:
            message, tool_info = self.get_chat_completion(
                agent=active_agent, history=history, model_override=model_override
            )

            assistant_message = {
                "role": "assistant",
                "sender": active_agent.name,
                "content": message.text,
            }
            # print(f'Active agent: {active_agent.name}')
            # print(f"message: {assistant_message}")
            # print('#############################################')

            history.append(assistant_message)

            if tool_info is None:
                print("No tool calls hence breaking")
                print("#############################################")
                break

            partial_response = await self.handle_tool_calls(
                agent, tool_info["tool"], tool_info["parameters"]
            )
            history.extend(partial_response.messages)

            if partial_response.agent:
                active_agent = partial_response.agent
                message.sender = active_agent.name
        return Response(
            messages=history[init_len:],
            agent=active_agent,
        )
