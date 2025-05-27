import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import time
from datetime import datetime

# Assuming these imports work with your project structure
from trento_agent_sdk.agent.agent import Agent
from trento_agent_sdk.tool.tool_manager import ToolManager
from trento_agent_sdk.agent.agent_manager import AgentManager
from trento_agent_sdk.memory.memory import LongMemory

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExpectedAgent(Enum):
    """Expected agent types for evaluation"""
    SUMMARIZER = "summarizer"
    RAG = "rag"

@dataclass
class TestCase:
    """Represents a single test case for evaluation"""
    question: str
    expected_agent: ExpectedAgent
    description: str
    category: str


@dataclass
class EvaluationResult:
    """Results of a single test case evaluation"""
    test_case: TestCase
    actual_agent_called: Optional[str]
    tools_called: List[str]
    execution_time: float
    success: bool
    response: str
    error: Optional[str] = None


class OrchestratorEvaluator:
    """Evaluates orchestrator agent performance"""
    
    def __init__(self, orchestrator_agent: Agent):
        self.orchestrator = orchestrator_agent
        self.test_cases = self._create_test_cases()
        
    def _create_test_cases(self) -> List[TestCase]:
        """Create predefined test cases for evaluation"""
        style = "technical"  # Can be: technical, bullet-points, standard, concise, detailed
        document_id = "1UBJJQ0V07DA92rtrT1CqI-nBwaVmCEXG"  # Example document ID
        return [
            # Summarization tasks
            TestCase(
                question=f"Can you summarize this document with ID {document_id} with style {style} for me?",
                expected_agent=ExpectedAgent.SUMMARIZER,
                description="Direct summarization request",
                category="summarization"
            ),
            TestCase(
                question=f"I need a brief summary of the content in bullet points. Document ID {document_id}, style {style} ",
                expected_agent=ExpectedAgent.SUMMARIZER,
                description="Specific format summarization",
                category="summarization"
            ),
            TestCase(
                question=f"Create a technical summary of this markdown document. Document ID {document_id}",
                expected_agent=ExpectedAgent.SUMMARIZER,
                description="Technical summarization request",
                category="summarization"
            ),
            TestCase(
                question=f"Please provide a concise overview of the main points. Document id {document_id}",
                expected_agent=ExpectedAgent.SUMMARIZER,
                description="Concise summarization request",
                category="summarization"
            ),
            
            # RAG/Question-answering tasks
            TestCase(
                question="What does the document say about artificial intelligence?",
                expected_agent=ExpectedAgent.RAG,
                description="Specific information retrieval",
                category="rag"
            ),
            TestCase(
                question="Can you find information about the methodology used?",
                expected_agent=ExpectedAgent.RAG,
                description="Methodology inquiry",
                category="rag"
            ),
            TestCase(
                question="What are the key findings mentioned in the research?",
                expected_agent=ExpectedAgent.RAG,
                description="Research findings query",
                category="rag"
            ),
            TestCase(
                question="Is there any mention of limitations in the study?",
                expected_agent=ExpectedAgent.RAG,
                description="Specific detail search",
                category="rag"
            ),
            TestCase(
                question="What does section 3.2 discuss?",
                expected_agent=ExpectedAgent.RAG,
                description="Section-specific query",
                category="rag"
            ),
    
            
            # Ambiguous cases (could go either way, but we'll set expectations)
            TestCase(
                question=f"Tell me about this document. ID {document_id}",
                expected_agent=ExpectedAgent.SUMMARIZER,
                description="Ambiguous document request (should lean toward summary)",
                category="ambiguous"
            ),
            TestCase(
                question="What can you tell me about the content?",
                expected_agent=ExpectedAgent.RAG,
                description="Ambiguous content request (should lean toward retrieval)",
                category="ambiguous"
            ),
        ]
    
    def _extract_agent_calls_from_history(self, chat_history: List[Dict[str, str]]) -> List[str]:
        """Extract which agents were called from chat history"""
        agents_called = []
        tools_called = []
        
        for entry in chat_history:
            if entry.get("role") == "system" and "Used tool" in entry.get("content", ""):
                content = entry["content"]
                # Extract tool name from content like "Used tool `delegate_task_to_agent_tool`"
                if "`delegate_task_to_agent_tool`" in content:
                    # Try to extract the agent name from the arguments
                    try:
                        # Look for agent_alias in the args
                        if "agent_alias" in content:
                            # Simple parsing - you might want to make this more robust
                            parts = content.split('"agent_alias":')
                            if len(parts) > 1:
                                agent_part = parts[1].split('"')[1]
                                agents_called.append(agent_part)
                    except:
                        agents_called.append("delegation_attempted")
                elif "`" in content:
                    # Extract other tool names
                    tool_start = content.find("`") + 1
                    tool_end = content.find("`", tool_start)
                    if tool_end > tool_start:
                        tools_called.append(content[tool_start:tool_end])
        
        return agents_called, tools_called
    
    async def evaluate_single_case(self, test_case: TestCase) -> EvaluationResult:
        """Evaluate a single test case"""
        logger.info(f"Evaluating: {test_case.question}")
        
        start_time = time.time()
        error = None
        actual_agent_called = None
        tools_called = []
        response = ""
        
        try:
            # Reset orchestrator state for clean test
            self.orchestrator.short_memory = [{"role": "system", "content": self.orchestrator.system_prompt}]
            self.orchestrator.chat_history = []
            
            # Run the orchestrator
            response = await self.orchestrator.run(test_case.question)
            
            # Extract which agents/tools were called
            agents_called, tools_called = self._extract_agent_calls_from_history(
                self.orchestrator.chat_history
            )
            
            if agents_called:
                actual_agent_called = agents_called[0]  # Take the first agent called
            elif tools_called:
                # If no agent delegation but tools were called, it's likely a direct response
                actual_agent_called = "direct"
            else:
                actual_agent_called = "direct"
            
        except Exception as e:
            error = str(e)
            logger.error(f"Error evaluating test case: {error}")
        
        execution_time = time.time() - start_time
        
        # Determine success
        success = self._is_evaluation_successful(test_case.expected_agent, actual_agent_called)
        
        return EvaluationResult(
            test_case=test_case,
            actual_agent_called=actual_agent_called,
            tools_called=tools_called,
            execution_time=execution_time,
            success=success,
            response=response,
            error=error
        )
    
    def _is_evaluation_successful(self, expected: ExpectedAgent, actual: Optional[str]) -> bool:
        """Determine if the evaluation was successful"""
        if actual is None:
            return False
            
        if expected == ExpectedAgent.SUMMARIZER:
            return actual == "summarizer"
        elif expected == ExpectedAgent.RAG:
            return actual == "rag"
        else:
            return False
    
    async def run_full_evaluation(self) -> Dict[str, Any]:
        """Run evaluation on all test cases"""
        logger.info(f"Starting evaluation with {len(self.test_cases)} test cases")
        
        results = []
        start_time = time.time()
        
        for i, test_case in enumerate(self.test_cases, 1):
            logger.info(f"Running test case {i}/{len(self.test_cases)}")
            result = await self.evaluate_single_case(test_case)
            results.append(result)
            
            # Add small delay between tests to avoid overwhelming the system
            await asyncio.sleep(1)
        
        total_time = time.time() - start_time
        
        # Generate summary statistics
        summary = self._generate_summary(results, total_time)
        
        return {
            "summary": summary,
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
    
    def _generate_summary(self, results: List[EvaluationResult], total_time: float) -> Dict[str, Any]:
        """Generate summary statistics from results"""
        total_tests = len(results)
        successful_tests = sum(1 for r in results if r.success)
        failed_tests = total_tests - successful_tests
        
        # Category breakdown
        category_stats = {}
        for result in results:
            category = result.test_case.category
            if category not in category_stats:
                category_stats[category] = {"total": 0, "successful": 0}
            category_stats[category]["total"] += 1
            if result.success:
                category_stats[category]["successful"] += 1
        
        # Agent delegation breakdown
        agent_stats = {}
        for result in results:
            agent = result.actual_agent_called or "none"
            if agent not in agent_stats:
                agent_stats[agent] = 0
            agent_stats[agent] += 1
        
        return {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "failed_tests": failed_tests,
            "success_rate": successful_tests / total_tests if total_tests > 0 else 0,
            "total_execution_time": total_time,
            "average_execution_time": total_time / total_tests if total_tests > 0 else 0,
            "category_breakdown": category_stats,
            "agent_delegation_stats": agent_stats
        }
    
    def print_detailed_results(self, evaluation_results: Dict[str, Any]):
        """Print detailed evaluation results"""
        summary = evaluation_results["summary"]
        results = evaluation_results["results"]
        
        print("\n" + "="*80)
        print("ORCHESTRATOR EVALUATION RESULTS")
        print("="*80)
        
        print(f"\nOVERALL PERFORMANCE:")
        print(f"Success Rate: {summary['success_rate']:.2%}")
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Successful: {summary['successful_tests']}")
        print(f"Failed: {summary['failed_tests']}")
        print(f"Total Time: {summary['total_execution_time']:.2f}s")
        print(f"Average Time per Test: {summary['average_execution_time']:.2f}s")
        
        print(f"\nCATEGORY BREAKDOWN:")
        for category, stats in summary["category_breakdown"].items():
            success_rate = stats["successful"] / stats["total"] if stats["total"] > 0 else 0
            print(f"  {category}: {success_rate:.2%} ({stats['successful']}/{stats['total']})")
        
        print(f"\nAGENT DELEGATION STATS:")
        for agent, count in summary["agent_delegation_stats"].items():
            print(f"  {agent}: {count} calls")
        
        print(f"\nDETAILED RESULTS:")
        print("-" * 80)
        
        for i, result in enumerate(results, 1):
            status = "✅ PASS" if result.success else "❌ FAIL"
            print(f"\n{i}. {status}")
            print(f"   Question: {result.test_case.question}")
            print(f"   Expected: {result.test_case.expected_agent.value}")
            print(f"   Actual: {result.actual_agent_called}")
            print(f"   Category: {result.test_case.category}")
            print(f"   Time: {result.execution_time:.2f}s")
            if result.tools_called:
                print(f"   Tools Called: {', '.join(result.tools_called)}")
            if result.error:
                print(f"   Error: {result.error}")
    
    def save_results_to_file(self, evaluation_results: Dict[str, Any], filename: str = None):
        """Save evaluation results to a JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"orchestrator_evaluation_{timestamp}.json"
        
        # Convert results to JSON-serializable format
        serializable_results = {
            "summary": evaluation_results["summary"],
            "timestamp": evaluation_results["timestamp"],
            "results": []
        }
        
        for result in evaluation_results["results"]:
            serializable_results["results"].append({
                "question": result.test_case.question,
                "expected_agent": result.test_case.expected_agent.value,
                "actual_agent_called": result.actual_agent_called,
                "tools_called": result.tools_called,
                "execution_time": result.execution_time,
                "success": result.success,
                "response": result.response,
                "error": result.error,
                "category": result.test_case.category,
                "description": result.test_case.description
            })
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(serializable_results, f, indent=2, ensure_ascii=False)
        
        print(f"\nResults saved to: {filename}")

async def register_all(agent_manager):
    # Summarization agent on port 8001
    card1 = await agent_manager.add_agent(
        alias="summarizer",
        server_url="http://localhost:8001"
    )
    print(f"Registered summarizer: {card1.name}")

    # RAG agent on port 8002
    card2 = await agent_manager.add_agent(
        alias="rag",
        server_url="http://localhost:8002"
    )
    print(f"Registered RAG agent: {card2.name}")


# Example usage function
async def main():
    """Example of how to use the evaluator"""
    import os
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
  
    tool_manager = ToolManager()
    agent_manager = AgentManager()
    await register_all(agent_manager)
    
    
    # Register your agents (adapt URLs as needed)
    await agent_manager.add_agent("summarizer", "http://localhost:8001")
    await agent_manager.add_agent("rag", "http://localhost:8002")
    
    memory_prompt= (
        "You are the LongMemory of an orchestator agent that have the role of choosing the right agent or tool to fulfill the user request.\n"
        "You will receive two inputs:\n"
        "1) existing_memories: a JSON array of {id, topic, description}\n"
        "2) chat_history: a string of the latest conversation.\n\n"
        "First you should extract which external agent or tool the orchestator choose to fulfill the user request and store the it to help the orchestator in future choises\n"
        "If you found usefull information in the chast_history, add them to the list. "
        "If this new information replace some of the existing memories, replace them. "
        "Analyze the chat and return a JSON object with exactly one field: \"memories_to_add\". "
        "The value must be either:\n"
        "  • A list of objects, each with exactly these fields:\n"
        "      – \"id\": the existing memory id to update, OR null if new\n"
        "      – \"topic\": a label for the general area of memory (e.g. \"agent_to_choose\", \"cuisine\").\n"
        "      – \"description\": a comprenshicve description about the usefull information to remember.\n"
        "  • The string \"NO_MEMORIES_TO_ADD\" if nothing has changed.\n"
        "Do NOT include any other fields or commentary."
    )

    memory = LongMemory(user_id="orchestrator", memory_prompt=memory_prompt)



    # 4) Define the orchestrator Agent itself
    orchestrator_agent = Agent(
        name="Orchestrator Agent",
        system_prompt=(
            "You are a highly capable orchestrator assistant. Your primary role is to understand user requests "
            "and decide the best course of action. This might involve using your own tools or delegating tasks "
            "to specialized remote agents if the request falls outside your direct capabilities or if a remote agent "
            "is better suited for the task.\n\n"
            "ALWAYS consider the following workflow:\n"
            "1. Understand the user's request.\n"
            "2. Check if any of your locally available tools can directly address the request. If yes, use them.\n"
            "3. If local tools are insufficient or if the task seems highly specialized, consider delegating. "
            "   Use the 'list_delegatable_agents' tool to see available agents and their capabilities. Do not ask the user, just  check available agents\n"
            "4. If you find a suitable agent, use the 'delegate_task_to_agent' tool to assign them the task (without asking the user, just assign the task). "
            "   Clearly formulate the sub-task for the remote agent.\n"
            "5. If no local tool or remote agent seems appropriate, or if you need to synthesize information, "
            "   respond to the user directly.\n"
            "You can have multi-turn conversations involving multiple tool uses and agent delegations to achieve complex goals.\n"
            "Be precise in your tool and agent selection. When delegating, provide all necessary context to the remote agent."
        ),
        tool_manager=tool_manager,
        agent_manager=agent_manager,
        model="gemini-2.0-flash",
        api_key=os.getenv("GEMINI_API_KEY"),
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        tool_required="auto",
        long_memory=memory,
    )

    # Create evaluator and run evaluation
    evaluator = OrchestratorEvaluator(orchestrator_agent)
    results = await evaluator.run_full_evaluation()
    
    # Print and save results
    evaluator.print_detailed_results(results)
    evaluator.save_results_to_file(results)


if __name__ == "__main__":
    asyncio.run(main())