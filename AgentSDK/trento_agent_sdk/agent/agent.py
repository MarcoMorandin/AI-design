import json
import logging
from math import e
from typing import List, Dict, Optional, Any, Literal, Annotated
from ..memory.memory import LongMemory
import openai
from pydantic import BaseModel, ConfigDict, Field

from ..tool.tool_manager import ToolManager
from ..tool.tool import Tool
from .agent_manager import AgentManager

logger = logging.getLogger(__name__)


class Agent(BaseModel):
    # allow ToolManager (an arbitrary class) in a pydantic model
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "Agent"
    model: str = "gemini-2.0-flash"
    tool_manager: ToolManager = None
    agent_manager: AgentManager = None
    long_memory: Optional[LongMemory] = None
    short_memory: List[Dict[str, str]] = []
    chat_history: List[Dict[str, str]] = []
    client: Optional[openai.OpenAI] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    final_tool: Optional[str] = None  # Name of the tool that should be called last
    user_id: str = "test_user"  # standard user id for the LongMemory
    tool_required: Literal["required", "auto"] = "required"
    validation: bool = False
    validation_tool_name: str = None
    system_prompt: str = (
        "You are a highly capable orchestrator assistant. Your primary role is to understand user requests "
        "and decide the best course of action. This might involve using your own tools or delegating tasks "
        "to specialized remote agents if the request falls outside your direct capabilities or if a remote agent "
        "is better suited for the task.\n\n"
        "ALWAYS consider the following workflow:\n"
        "1. Understand the user's request thoroughly.\n"
        "2. Check if any of your locally available tools can directly address the request. If yes, use them.\n"
        "3. If local tools are insufficient or if the task seems highly specialized, consider delegating. "
        "   Use the 'list_delegatable_agents' tool to see available agents and their capabilities.\n"
        "4. If you find a suitable agent, use the 'delegate_task_to_agent' tool to assign them the task. "
        "   Clearly formulate the sub-task for the remote agent.\n"
        "5. If no local tool or remote agent seems appropriate, or if you need to synthesize information, "
        "   respond to the user directly.\n"
        "You can have multi-turn conversations involving multiple tool uses and agent delegations to achieve complex goals.\n"
        "Be precise in your tool and agent selection. When delegating, provide all necessary context to the remote agent."
    )
    validation: bool = False
    validation_tool_name: str = None

    def __init__(self, **data):
        super().__init__(**data)
        self.client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
        if not self.short_memory:
            self.short_memory = [{"role": "system", "content": self.system_prompt}]
        if self.long_memory is None:
            self.long_memory = LongMemory(user_id=self.user_id)

        if self.agent_manager is not None:
            self._register_internal_tools()
            print(self.tool_manager.list_tools())
        else:
            print("No agent manager provided, no internal tools registered")

    def _register_internal_tools(self):
        """Registers tools specific to agent interaction."""
        self.tool_manager.add_tool(
            fn=self.list_delegatable_agents_tool, name="list_delegatable_agents_tool"
        )

        self.tool_manager.add_tool(
            # Parameters will be dynamically added by _convert_tools_format based on the function signature
            # or defined explicitly here if needed for more complex schemas.
            fn=self.delegate_task_to_agent_tool,
            name="delegate_task_to_agent_tool",
        )

    async def list_delegatable_agents_tool(self) -> List[Dict[str, Any]]:
        """
        Return a list with one entry per registered remote agent.

        The format mirrors AgentManager.list_delegatable_agents().
        """
        return self.agent_manager.list_delegatable_agents()

    async def delegate_task_to_agent_tool(
        self,
        agent_alias: Annotated[
            str,
            Field(
                description="Alias of the remote agent to which the task should be delegated"
            ),
        ],
        message: Annotated[
            str,
            Field(description="The user request / task description to forward"),
        ],
        timeout: Annotated[
            Optional[float],
            Field(
                description="Optional timeout in seconds to wait for completion",
                examples=[30],
            ),
        ] = None,
    ) -> str:
        """
        Send *message* to the chosen agent and return **plain text** output.

        If the agent returns multiple text parts they are concatenated with
        new‑lines.
        """
        resp = await self.agent_manager.delegate_task_to_agent(
            alias=agent_alias,
            message=message,
            timeout=timeout,
        )
        return self.agent_manager.extract_text(resp)

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

    # validate the result and insert into long memory
    async def validate_result(self, tool_name, args):
        logger.info(f"Validation tool {tool_name} called, executing it and terminating")
        result = await self.tool_manager.call_tool(tool_name, args)
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
            self.long_memory.insert_into_long_memory_with_update(serialized_result)

        except Exception as e:
            logger.error(f"Error serializing tool result: {e}")
            serialized_result = str(result)
        return serialized_result

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
            self.short_memory.append({"role": "user", "content": user_msg})
            self.chat_history.append({"role": "user", "content": user_msg})

            # Retrieve from long memory
            mems = self.long_memory.get_memories(user_msg, top_k=5)
            if mems:
                mem_texts = [f"- [{m['topic']}] {m['description']}" for m in mems]
                mem_block = "Relevant past memories:\n" + "\n".join(mem_texts)
                self.short_memory.append({"role": "system", "content": mem_block})

            # print(mems)

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
                    messages=self.short_memory,
                    tools=tools,
                    tool_choice=self.tool_required,
                    temperature=temperature,
                )

                # Add model's response to conversation
                self.short_memory.append(response.choices[0].message)
                # self.short_memory.append(self._to_dict(response.choices[0].message))

                # logger.info(f"response_content: {response.choices[0].message}")
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
                        args_string = tool_call.function.arguments
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

                                serialized_result = ""
                                try:
                                    # Handle different result types appropriately
                                    if isinstance(result, str):
                                        serialized_result = result
                                    elif isinstance(
                                        result, (list, dict, int, float, bool)
                                    ):
                                        serialized_result = json.dumps(result)
                                    elif hasattr(result, "_dict_"):
                                        serialized_result = json.dumps(result._dict_)
                                    else:
                                        serialized_result = str(result)

                                    logger.info(
                                        f"Tool {tool_name} returned result: {serialized_result[:100]}..."
                                    )
                                    self.long_memory.insert_into_long_memory_with_update(
                                        serialized_result
                                    )

                                except Exception as e:
                                    logger.error(f"Error serializing tool result: {e}")
                                    serialized_result = str(result)

                                # Add tool result to the conversation
                                self.short_memory.append(
                                    {
                                        "role": "tool",
                                        "tool_call_id": call_id,
                                        "content": serialized_result,
                                    }
                                )

                                self.chat_history.append(
                                    {
                                        "role": "system",
                                        "content": f"Used tool `{tool_name}` with args {args_string} that returned JSON:\n{serialized_result}",
                                    }
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

                        # validate result
                        if self.validation and tool_name == self.validation_tool_name:
                            self.validate_result(tool_name, args)

                        # print(f"Calling tool {tool_name} with args: {args}")

                        logger.info(f"Calling tool {tool_name}")
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
                                elif hasattr(result, "_dict_"):
                                    serialized_result = json.dumps(result._dict_)
                                else:
                                    serialized_result = str(result)

                                logger.info(
                                    f"Tool {tool_name} returned result: {serialized_result[:100]}..."
                                )
                                self.long_memory.insert_into_long_memory_with_update(
                                    serialized_result
                                )

                            except Exception as e:
                                logger.error(f"Error serializing tool result: {e}")
                                serialized_result = str(result)

                            # Add tool result to the conversation
                            self.short_memory.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": call_id,
                                    "content": serialized_result,
                                }
                            )

                            self.chat_history.append(
                                {
                                    "role": "system",
                                    "content": f"Used tool `{tool_name}` with args {args_string} that returned JSON:\n{serialized_result}",
                                }
                            )
                        except Exception as e:
                            error_message = f"Error calling tool {tool_name}: {str(e)}"
                            logger.error(error_message)
                            self.short_memory.append(
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
                self.short_memory.append(
                    {
                        "role": "system",
                        "content": "You've reached the maximum number of allowed iterations. Please provide a final response based on the information you have.",
                    }
                )

            logger.error("SHORT MOMORY")
            logger.error(self.chat_history)
            self.long_memory.insert_into_long_memory_with_update(self.chat_history)

            final_response = self.client.chat.completions.create(
                model=self.model, messages=self.short_memory, temperature=temperature
            )

            return final_response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error running agent: {e}")
            return f"Error: {str(e)}"
