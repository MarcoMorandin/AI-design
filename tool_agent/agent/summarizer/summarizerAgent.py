from tool.tool_manager import ToolManager
from tool.get_text.get_text import get_text
from tool.summarizer_type.get_correct_format_prompt import get_correct_format_prompt
from tool.summarizer_type.get_summarize_chunk_prompt import get_prompt_to_summarize_chunk
from tool.summarizer_type.get_final_summary_prompt import get_final_summary_prompt
from agent.agent import Agent, Swarm, pretty_print_messages
import asyncio

manager=ToolManager()
manager.add_tool(get_text)
manager.add_tool(get_correct_format_prompt)
manager.add_tool(get_prompt_to_summarize_chunk)
manager.add_tool(get_final_summary_prompt)

summarizerAgent=Agent(name="Summarizer Agent", 
    instructions="You are an agent that get a text and provide the summary of it. If you think the text is to long to provide a good summary you can split, do the summary of the chunks and than put all togheter. If the summary contains some formulas, you must ensure a valid format of them", 
    tool_manager=manager)


client = Swarm()
print("Starting Single Agent - Weather Agent")
print('Say something')

async def main():
    messages = []
    agent = summarizerAgent

    while True:
        user_input = input("\033[90mUser\033[0m: ")
        messages.append({"role": "user", "content": user_input})

        response = await client.run(agent=agent, messages=messages)
        pretty_print_messages(response.messages)

        messages.extend(response.messages)
        agent = response.agent

if __name__ == "__main__":
    asyncio.run(main())
