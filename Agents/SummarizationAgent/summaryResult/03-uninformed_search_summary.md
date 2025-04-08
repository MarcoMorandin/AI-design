# Uninformed Search Algorithms: A Lab Session

This document outlines a lab session focused on understanding and implementing uninformed search algorithms. We will explore the fundamental concepts of problem-solving agents, search problems, and search algorithms, ultimately delving into the mechanics of breadth-first search (BFS), depth-first search (DFS), and iterative deepening.

## Introduction: Problem-Solving Agents and Search

Our journey begins with the idea of **problem-solving agents**. These agents operate by formulating a plan and executing actions sequentially to achieve a goal. They excel in environments where they can effectively plan a series of steps. The ability to plan hinges on possessing sufficient information about the environment and the consequences of actions.

The core of problem-solving involves defining a **search problem**.  A search problem is typically represented graphically, visualizing the possible states and transitions within the search space.  A **search algorithm**, in turn, systematically explores this search space, constructing either a search tree or a Directed Acyclic Graph (DAG) to find a solution path.

## Uninformed Search: Blindly Navigating the Space

This lab emphasizes **uninformed search algorithms**. These algorithms operate without any prior knowledge or heuristics about the search space. They rely solely on the problem definition to guide their exploration.

Key terms and concepts critical to understanding uninformed search:

*   **Expansion:** The process of generating successor states from a given state.
*   **Generation:** Creating new states based on the application of actions to existing states.
*   **Tree-like vs. Graph-like Search:** Tree-like search does not track visited states, potentially leading to redundant exploration of cycles. Graph-like search keeps track of visited states to prevent cycles and redundant exploration.
*   **Frontier:** The set of nodes (states) that are currently known but not yet expanded.  These are the "edges" of the explored territory.
*   **Reached States:** The set of all states that have been visited during the search.

## Best-First Search: A Template for Exploration

Uninformed search algorithms often leverage a general template known as **Best-First Search**. This template defines the basic structure of how we will select states from the frontier for expansion. Different uninformed search algorithms differ primarily in how they prioritize nodes in the frontier.

## Specific Uninformed Search Algorithms

We will explore three key uninformed search algorithms:

*   **Breadth-First Search (BFS):** Explores the search space level by level. It expands the shallowest nodes in the frontier first.

*   **Depth-First Search (DFS):** Explores the search space by going as deep as possible along each branch before backtracking. It expands the deepest nodes in the frontier first.  A critical distinction exists between **tree-like DFS**, which doesn't prevent cycles, and **graph-like DFS**, which avoids revisiting already explored states.

*   **Iterative Deepening:** Combines the space efficiency of DFS with the completeness of BFS. It performs a series of depth-limited DFS searches, incrementing the depth limit with each iteration.

## Understanding Through Example (Ex. 1)

The following example demonstrates the execution of BFS, DFS (tree-like and graph-like), and iterative deepening on a specific search problem. This example is crucial for understanding the nuances of each algorithm.

**Scenario:** (Detailed problem description here - the original document example should be included here, likely with a diagram of the search space.)

**Algorithm Walkthroughs:**

The following sections will demonstrate each algorithm step-by-step, showing the evolution of the `frontier` and the `reached` set (where applicable).

*   **Breadth-First Search (BFS):** (Detailed step-by-step example with frontier updates)
*   **Depth-First Search (Tree-like):** (Detailed step-by-step example with frontier updates)
    *   *Note the potential for cycles in this tree-like implementation.*
*   **Depth-First Search (Graph-like):** (Detailed step-by-step example with frontier and reached set updates)
    *   *Notice how the `reached` set prevents cycles and redundant exploration.*
*   **Iterative Deepening:** (Detailed step-by-step example showing how depth limits are increased and frontiers are cleared at each iteration)

## Quick Questions: Test Your Knowledge

Answer the following questions to reinforce your understanding:

*   [Question related to BFS]
*   [Question related to DFS]
*   [Question related to Uniform-Cost Search (even though it's not purely uninformed, it's relevant)]
