import os, sys

# insert the path to tool_agent/ into sys.path
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
))

from tool.tool_manager import ToolManager
from tool.get_text.get_text import get_text
from tool.summarizer_type.get_correct_format_prompt import get_correct_format_prompt
from tool.summarizer_type.get_summarize_chunk_prompt import get_prompt_to_summarize_chunk
from tool.summarizer_type.get_final_summary_prompt import get_final_summary_prompt
from tool.chunker.chunker_tool import get_chunks
from agent.agent import Agent, Swarm, pretty_print_messages
import asyncio
import streamlit as st

manager=ToolManager()
manager.add_tool(get_text)
manager.add_tool(get_chunks)
manager.add_tool(get_correct_format_prompt)
manager.add_tool(get_prompt_to_summarize_chunk)
manager.add_tool(get_final_summary_prompt)

summarizerAgent=Agent(name="Summarizer Agent", 
    instructions="You are an agent that get a text and provide the summary of it. If you think the text is to long to provide a good summary you can split, do the summary of the chunks and than put all togheter. At the end, if the summary contains some formulas, you must ensure a valid format of them", 
    tool_manager=manager)

client = Swarm()
st.title("Summarizer Agent")
st.write("Enter text to summarize:")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "agent" not in st.session_state:
    st.session_state.agent = summarizerAgent

user_input = st.text_area("Your input", key="user_input")
if st.button("Summarize"):
    if user_input.strip():
        st.session_state.messages.append({"role": "user", "content": user_input})
        async def run_agent():
            response = await client.run(agent=st.session_state.agent, messages=st.session_state.messages)
            return response
        response = asyncio.run(run_agent())
        pretty_print_messages(response.messages)
        st.session_state.messages.extend(response.messages)
        st.session_state.agent = response.agent

# Optionally, display the conversation history
for msg in st.session_state.messages:
    st.write(f"**{msg['role'].capitalize()}**: {msg['content']}")
