import json
import logging
from typing import List, Dict, Optional, Any, Literal

from AgentSDK.trento_agent_sdk.memory.memory import LongMemory
import openai
from pydantic import BaseModel, ConfigDict

from ..tool.tool_manager import ToolManager
from agent_manager import AgentManager

from ..a2a.models.Types import (
    SendTaskRequest,
    SendTaskResponse,
    GetTaskRequest,
    GetTaskResponse,
    CancelTaskRequest,
    CancelTaskResponse,
)

logger = logging.getLogger(__name__)


class Agent(BaseModel):
    # allow ToolManager (an arbitrary class) in a pydantic model
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "Agent"
    model: str = "gemini-2.0-flash"
    tool_manager: ToolManager = None
    agent_manager: AgentManager = None
    long_memory: LongMemory = Field(default_factory=LongMemory)
    short_memory: List[Dict[str, str]] = []
    client: Optional[openai.OpenAI] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    final_tool: Optional[str] = None  # Name of the tool that should be called last
    tool_required: Literal["required", "auto"] = "required"
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

    def __init__(self, **data):
        super().__init__(**data)
        client_kwargs = {}
        if self.api_key:
            client_kwargs["api_key"] = self.api_key
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        self.client = openai.OpenAI(**client_kwargs)
        if not self.short_memory:
            self.short_memory = [{"role": "system", "content": self.system_prompt}]

        self._register_internal_tools()

    def _register_internal_tools(self):
        """Registers tools specific to agent interaction."""
        list_agents_tool = Tool(
            name="list_delegatable_agents",
            description="Lists all available remote agents you can delegate tasks to, along with their capabilities (descriptions). Use this to discover which agent might be suitable for a specific sub-task.",
            func=self._list_delegatable_agents_tool
        )
        self.tool_manager.register_tool(list_agents_tool)

        delegate_task_tool = Tool(
            name="delegate_task_to_agent",
            description="Delegates a task to a specified remote agent. You must provide the 'agent_alias' (from 'list_delegatable_agents') and the 'task_message' (a clear instruction for the remote agent).",
            # Parameters will be dynamically added by _convert_tools_format based on the function signature
            # or defined explicitly here if needed for more complex schemas.
            func=self._delegate_task_to_agent_tool
        )
        self.tool_manager.register_tool(delegate_task_tool)
        
    async def _list_delegatable_agents_tool(self) -> str:
        """Implementation for the list_delegatable_agents tool."""
        logger.info("Executing internal tool: list_delegatable_agents")
        agent_aliases = self.agent_manager.list_agents()
        if not agent_aliases:
            return "No remote agents are currently available for delegation."

        agent_details = []
        for alias in agent_aliases:
            try:
                card = self.agent_manager.get_agent_card(alias)
                agent_details.append({
                    "alias": alias,
                    "name": card.name,
                    "description": card.description,
                    "skills": card.skills if card.skills else "Not specified"
                })
            except Exception as e:
                logger.error(f"Could not retrieve card for agent {alias}: {e}")
                agent_details.append({"alias": alias, "name": "Unknown", "description": f"Error retrieving details: {e}"})
        return json.dumps(agent_details)

    async def _delegate_task_to_agent_tool(self, agent_alias: str, task_message: str, session_id: Optional[str] = None, wait_for_completion: bool = True) -> str:
        """
        Implementation for the delegate_task_to_agent tool.
        Args:
            agent_alias: The alias of the agent to delegate the task to.
            task_message: The message/task description for the remote agent.
            session_id: Optional session ID for the task.
            wait_for_completion: If true, waits for the remote agent to complete the task.
        """
        logger.info(f"Executing internal tool: delegate_task_to_agent (alias: {agent_alias}, message: '{task_message[:50]}...', wait: {wait_for_completion})")
        try:
            response = await self.agent_manager.call_agent(
                alias=agent_alias,
                message=task_message, 
                session_id=session_id,
                wait=wait_for_completion
            )
            # Process the response (SendTaskResponse or GetTaskResponse)
            if isinstance(response, GetTaskResponse): # If waited
                return json.dumps({
                    "task_id": response.id,
                    "status": response.result.status, # Or response.result.status.state from your A2AClient
                    "result": response.result # Or response.result.message.parts[0].text
                })
            elif isinstance(response, SendTaskResponse): # If not waited
                 return json.dumps({
                    "task_id": response.id, # Or response.result.task.id
                    "status": "SENT",
                    "details": "Task sent to remote agent. Poll separately if needed."
                })
            return json.dumps(response) # Fallback, adjust based on actual response structure
        except KeyError:
            return json.dumps({"error": f"Agent with alias '{agent_alias}' not found."})
        except Exception as e:
            logger.error(f"Error delegating task to agent {agent_alias}: {e}")
            return json.dumps({"error": f"Failed to delegate task to {agent_alias}: {str(e)}"})
        

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
            self.short_memory.append({"role": "user", "content": user_msg})
            
            # Retrieve from long memory
            mems = self.long_memory.get_memories(user_msg, top_k=5)
            if mems:
                mem_texts = [
                    f"- [{m['topic']}] {m['description']}" for m in mems
                ]
                mem_block = "Relevant past memories:\n" + "\n".join(mem_texts)
                self.short_memory.append({"role": "system", "content": mem_block})


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
                    tool_choice="required",
                    temperature=temperature,
                )

                # Add model's response to conversation
                #messages.append(response.choices[0].message)

                self.short_memory.append({
                    "role": response.choices[0].message.role,
                    "content": response.choices[0].message.content
                })

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
                            self.short_memory.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": call_id,
                                    "content": serialized_result,
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

            # Get final response from the model if no final tool was called during iterations
            final_response = self.client.chat.completions.create(
                model=self.model, messages=self.short_memory, temperature=temperature
            )

            # Update long memory
            self.long_memory.insert_into_long_memory_with_update(self.short_memory)
            return final_response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error running agent: {e}")
            return f"Error: {str(e)}"
