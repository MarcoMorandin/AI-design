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
import logging
from .agent import Agent
from .models import Response, Result

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class Swarm:
    # Questo rappresenta l'orchestrator ma, TODO: ce ne sono di due tipi (manager e decentralized) → quando mettiamo più agenti poi vediamo come fare
    def __init__(
        self,
        client,
    ):
        """Initialize Swarm with a client for language model interaction."""
        self.client = client

    def get_chat_completion(self, agent: Agent, history: List, model_override: str):
        """Generate a response from the language model."""

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

        try:
            response = self.client.models.generate_content(
                model=model_name, contents=[prompt]
            )
            tool_info = self._parse_tool_selection(response.text)
            logger.debug(f"TOOL INFO: {tool_info}")
            return response, tool_info
        except Exception as e:
            raise RuntimeError(f"Failed to get chat completion: {e}")

    def _parse_tool_selection(self, content: str):
        logger.debug("CONTENT")
        logger.debug("#############################################")
        logger.debug(content)
        logger.debug("#############################################")
        """Extract tool selection information from the response text."""
        if "TOOL:" in content:
            try:
                # il reasoning per ora non ci serve
                tool_match = re.search(
                    r"TOOL:(.*?)(?=PARAMETERS:|$)", content, re.DOTALL
                )
                params_match = re.search(r"PARAMETERS:(.*?)$", content, re.DOTALL)

                if tool_match:
                    tool_name = tool_match.group(1).strip()
                    params_str = params_match.group(1).strip() if params_match else "{}"

                    try:
                        logger.debug(f"PARAM_BEFORE_JSON: {params_str}\n")
                        parameters = ast.literal_eval(params_str)

                        logger.debug(f"PARAMETERS: {parameters}")
                    except json.JSONDecodeError:
                        logger.error(f"PARAMETERS: VUOTO")
                        parameters = {}

                    return {
                        "tool": tool_name,
                        "parameters": parameters,
                    }
            except Exception as e:
                logger.error(f"Error parsing tool selection: {e}")
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
        logger.debug(f"CALLED FUNCTION {tool_name} WITH ARGS: {parameter}")

        raw_result = await agent.tool_manager.call_tool(tool_name, parameter)
        logger.debug(f"AND OBTAINED RESULTs: {raw_result}")
        logger.debug("#############################################")
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

        while len(history) - init_len < max_turns and active_agent:
            message, tool_info = self.get_chat_completion(
                agent=active_agent, history=history, model_override=model_override
            )

            assistant_message = {
                "role": "assistant",
                "sender": active_agent.name,
                "content": message.text,
            }

            history.append(assistant_message)

            if tool_info is None:
                logger.debug("No tool calls hence breaking")
                logger.debug("#############################################")
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
