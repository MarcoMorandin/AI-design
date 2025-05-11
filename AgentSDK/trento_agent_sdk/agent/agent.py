import json
import logging
from typing import List, Dict, Optional, Any

import openai
from pydantic import BaseModel, ConfigDict

from ..tool.tool_manager import ToolManager

logger = logging.getLogger(__name__)


class Agent(BaseModel):
    # allow ToolManager (an arbitrary class) in a pydantic model
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "Agent"
    model: str = "gemini-2.0-flash"
    tool_manager: ToolManager = None
    client: Optional[openai.OpenAI] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    final_tool: Optional[str] = None  # Name of the tool that should be called last
    system_prompt: str = (
        "You are a helpful assistant that always uses tools when available. Never try to solve tasks yourself if there's a relevant tool available. Always use the appropriate tool for calculations, lookups, or data processing tasks."
    )

    def __init__(self, **data):
        super().__init__(**data)
        client_kwargs = {}
        if self.api_key:
            client_kwargs["api_key"] = self.api_key
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        self.client = openai.OpenAI(**client_kwargs)

    def _convert_tools_format(self) -> List[Dict]:
        """Convert tools from the tool manager to OpenAI function format"""
        tool_list = []

        try:
            # Get all registered tools
            tools = self.tool_manager.list_tools()
            for tool in tools:
                # Get the tool info already in OpenAI format
                tool_info = tool.get_tool_info()
                if tool_info:
                    tool_list.append(tool_info)
                    logger.info(f"Added tool: {tool.name}")

        except Exception as e:
            logger.error(f"Error converting tools format: {e}")

        return tool_list

    async def run(
        self,
        user_msg: str,
        temperature: float = 0.7,
        max_iterations: int = 30,  # Add a limit to prevent infinite loops
    ) -> str:
        """
        Run the agent with the given user message.

        Args:
            user_msg: The user's message
            temperature: Temperature for the model (randomness)
            max_iterations: Maximum number of tool call iterations to prevent infinite loops

        Returns:
            The model's final response as a string, or the output of the final tool if specified
        """

        try:
            # Build initial messages
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_msg},
            ]

            # Get available tools
            tools = self._convert_tools_format()

            # Keep track of iterations
            iteration_count = 0

            # Continue running until the model decides it's done,
            # or we reach the maximum number of iterations
            while iteration_count < max_iterations:
                iteration_count += 1
                logger.info(f"Starting iteration {iteration_count} of {max_iterations}")

                # Get response from model
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=tools,
                    tool_choice="required",
                    temperature=temperature,
                )

                # Add model's response to conversation
                messages.append(response.choices[0].message)

                # Check if the model used a tool
                if (
                    hasattr(response.choices[0].message, "tool_calls")
                    and response.choices[0].message.tool_calls
                ):
                    logger.info(
                        "Model used tool(s), executing and continuing conversation"
                    )

                    # Process and execute each tool call
                    for tool_call in response.choices[0].message.tool_calls:
                        tool_name = tool_call.function.name
                        args = json.loads(tool_call.function.arguments)
                        call_id = tool_call.id

                        # If this is the final tool, execute it immediately and terminate
                        if self.final_tool and tool_name == self.final_tool:
                            logger.info(
                                f"Final tool {tool_name} called, executing it and terminating"
                            )
                            try:
                                # Call the final tool directly
                                result = await self.tool_manager.call_tool(
                                    tool_name, args
                                )

                                # Directly return the result
                                logger.info(
                                    f"Final tool executed successfully, returning its output as the final result"
                                )
                                return (
                                    result
                                    if isinstance(result, str)
                                    else json.dumps(result)
                                )

                            except Exception as e:
                                error_message = (
                                    f"Error executing final tool {tool_name}: {str(e)}"
                                )
                                logger.error(error_message)
                                # Return error message if the final tool fails
                                return error_message

                        logger.info(f"Calling tool {tool_name} with args: {args}")
                        try:
                            result = await self.tool_manager.call_tool(tool_name, args)

                            # Properly serialize the result regardless of type
                            serialized_result = ""
                            try:
                                # Handle different result types appropriately
                                if isinstance(result, str):
                                    serialized_result = result
                                elif isinstance(result, (list, dict, int, float, bool)):
                                    serialized_result = json.dumps(result)
                                elif hasattr(result, "__dict__"):
                                    serialized_result = json.dumps(result.__dict__)
                                else:
                                    serialized_result = str(result)

                                logger.info(
                                    f"Tool {tool_name} returned result: {serialized_result[:100]}..."
                                )
                            except Exception as e:
                                logger.error(f"Error serializing tool result: {e}")
                                serialized_result = str(result)

                            # Add tool result to the conversation
                            messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": call_id,
                                    "content": serialized_result,
                                }
                            )
                        except Exception as e:
                            error_message = f"Error calling tool {tool_name}: {str(e)}"
                            logger.error(error_message)
                            messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": call_id,
                                    "content": json.dumps({"error": error_message}),
                                }
                            )
                else:
                    # If no tool was called, the model has finished its work
                    logger.info("Model did not use tools, conversation complete")
                    break

            # If we've reached the maximum number of iterations, log a warning
            if iteration_count >= max_iterations:
                logger.warning(
                    f"Reached maximum number of iterations ({max_iterations})"
                )
                # Append a message to let the model know it needs to wrap up
                messages.append(
                    {
                        "role": "system",
                        "content": "You've reached the maximum number of allowed iterations. Please provide a final response based on the information you have.",
                    }
                )

            # Get final response from the model if no final tool was called during iterations
            final_response = self.client.chat.completions.create(
                model=self.model, messages=messages, temperature=temperature
            )

            return final_response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error running agent: {e}")
            return f"Error: {str(e)}"
