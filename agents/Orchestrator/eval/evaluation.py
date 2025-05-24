import asyncio
import json
import os
import sys
from typing import Dict, List, Tuple
import pandas as pd
from dotenv import load_dotenv

from trento_agent_sdk.a2a_client import A2AClient

# Load environment variables
load_dotenv()

# Test cases with expected agent routing
TEST_CASES = [
    {
        "query": "Can you summarize this document for me? It's about machine learning concepts.",
        "expected_agent": "summarizer",
        "category": "summarization"
    },
    {
        "query": "I need a summary of this PDF about neural networks.",
        "expected_agent": "summarizer",
        "category": "summarization"
    },
    {
        "query": "Please create a concise summary of this research paper.",
        "expected_agent": "summarizer",
        "category": "summarization"
    },
    {
        "query": "What does the document say about transformer architectures?",
        "expected_agent": "rag",
        "category": "document_query"
    },
    {
        "query": "Can you find information about gradient descent in the document?",
        "expected_agent": "rag",
        "category": "document_query"
    },
    {
        "query": "What are the key points mentioned about reinforcement learning?",
        "expected_agent": "rag",
        "category": "document_query"
    },
    {
        "query": "What's the weather like today?",
        "expected_agent": None,  # Orchestrator should handle directly or indicate no suitable agent
        "category": "general"
    },
    {
        "query": "Tell me a joke.",
        "expected_agent": None,
        "category": "general"
    }
]

class OrchestratorEvaluator:
    def __init__(self, orchestrator_url: str = "http://localhost:8000"):
        self.orchestrator_url = orchestrator_url
        self.results = []
        
    async def evaluate_query(self, query: str, expected_agent: str, category: str) -> Dict:
        """Send a query to the orchestrator and evaluate its routing decision"""
        print(f"\nTesting query: {query}")
        print(f"Expected agent: {expected_agent}")
        
        async with A2AClient(self.orchestrator_url) as client:
            # Send the query to the orchestrator
            send_resp = await client.send_task(query)
            task_id = send_resp.result.id
            
            # Wait for the orchestrator to process the request
            final_resp = await client.wait_for_task_completion(task_id)
            
            # Extract the full response text
            response_text = ""
            if (final_resp.result and final_resp.result.status and 
                final_resp.result.status.message and final_resp.result.status.message.parts):
                for part in final_resp.result.status.message.parts:
                    if hasattr(part, "text") and part.text:
                        response_text += part.text
            
            # Extract the agent used from the response
            # This requires parsing the response to find which agent was delegated to
            agent_used = self._extract_agent_from_response(response_text)
            
            # Determine if the routing was correct
            is_correct = (agent_used == expected_agent) or (agent_used is None and expected_agent is None)
            
            result = {
                "query": query,
                "expected_agent": expected_agent,
                "actual_agent": agent_used,
                "category": category,
                "is_correct": is_correct,
                "response": response_text
            }
            
            self.results.append(result)
            print(f"Agent used: {agent_used}")
            print(f"Correct routing: {is_correct}")
            
            return result
    
    def _extract_agent_from_response(self, response: str) -> str:
        """Extract which agent was used from the orchestrator's response"""
        response = response.lower()
        
        # Look for delegation patterns in the response
        if "delegated to summarizer" in response or "using summarizer agent" in response or "summarization agent" in response:
            return "summarizer"
        elif "delegated to rag" in response or "using rag agent" in response or "retrieval augmented generation agent" in response:
            return "rag"
        
        # Check for tool usage patterns that might indicate which agent was used
        if "delegate_task_to_agent_tool" in response and "summarizer" in response:
            return "summarizer"
        if "delegate_task_to_agent_tool" in response and "rag" in response:
            return "rag"
        
        # If no clear delegation was found
        return None
    
    async def run_evaluation(self, test_cases: List[Dict] = None) -> Dict:
        """Run the evaluation on all test cases"""
        if test_cases is None:
            test_cases = TEST_CASES
        
        for test_case in test_cases:
            await self.evaluate_query(
                test_case["query"], 
                test_case["expected_agent"],
                test_case["category"]
            )
        
        return self.generate_report()
    
    def generate_report(self) -> Dict:
        """Generate a summary report of the evaluation results"""
        total_tests = len(self.results)
        correct_routings = sum(1 for result in self.results if result["is_correct"])
        accuracy = correct_routings / total_tests if total_tests > 0 else 0
        
        # Calculate accuracy by category
        categories = {}
        for result in self.results:
            category = result["category"]
            if category not in categories:
                categories[category] = {"total": 0, "correct": 0}
            
            categories[category]["total"] += 1
            if result["is_correct"]:
                categories[category]["correct"] += 1
        
        category_accuracy = {
            category: data["correct"] / data["total"] if data["total"] > 0 else 0
            for category, data in categories.items()
        }
        
        report = {
            "total_tests": total_tests,
            "correct_routings": correct_routings,
            "overall_accuracy": accuracy,
            "category_accuracy": category_accuracy,
            "detailed_results": self.results
        }
        
        # Print summary report
        print("\n===== EVALUATION REPORT =====")
        print(f"Total tests: {total_tests}")
        print(f"Correct routings: {correct_routings}")
        print(f"Overall accuracy: {accuracy:.2%}")
        print("\nAccuracy by category:")
        for category, acc in category_accuracy.items():
            print(f"  {category}: {acc:.2%}")
        
        return report
    
    def save_results(self, filename: str = "orchestrator_evaluation_results.json"):
        """Save the evaluation results to a file"""
        report = self.generate_report()
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Also save as CSV for easier analysis
        df = pd.DataFrame(self.results)
        df.to_csv(f"{filename.split('.')[0]}.csv", index=False)
        
        print(f"\nResults saved to {filename} and {filename.split('.')[0]}.csv")

async def main():
    evaluator = OrchestratorEvaluator()
    await evaluator.run_evaluation()
    evaluator.save_results()

if __name__ == "__main__":
    asyncio.run(main())