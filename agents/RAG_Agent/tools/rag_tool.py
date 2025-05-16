from .rag_class import RAG
import requests
from dotenv import load_dotenv
import os

import json

load_dotenv()


class RAG_tool:
    def __init__(self, user_id):
        self.chat_with_document = RAG(user_id)
        self.grok_chat_url = "https://api.groq.com/openai/v1/chat/completions"
        self.grok_api_key = os.getenv("GROQ_API_KEY")

    def get_response(self, question):
        """
        Retrieves relevant knowledge from the user's knowledge base based on the input question.
        
        Args:
            question (str): The user's question or query to search for in the knowledge base.
            
        Returns:
            List[str]: A list of text chunks from the knowledge base that are most relevant 
                      to the input question
        """
        return self.chat_with_document.retrieve_relevant_knowledge(question)

if __name__ == "__main__":
    rag_tool = RAG_tool("RAG_usertest_user")
    print(rag_tool.get_response("Earth radiates"))


