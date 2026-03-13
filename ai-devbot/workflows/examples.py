"""
Example Workflows Module

Example workflows demonstrating how to use the AI DevBot system.
"""

import asyncio
from typing import Dict, Any

from agents.spec_agent import SpecAgent
from agents.code_agent import CodeAgent
from agents.test_agent import TestAgent
from agents.debug_agent import DebugAgent
from agents.deploy_agent import DeployAgent
from agents.base_agent import Task
from workflows.orchestration import Orchestrator, TaskStatus
from tools.claude_cli import ClaudeCLITool


async def example_spec_to_code_workflow(requirement: str):
    """
    Example workflow: Generate spec, then generate code from spec.
    """
    print(f"=== Starting Spec-to-Code Workflow ===")
    print(f"Requirement: {requirement}")

    # Create Claude CLI tool
    claude = ClaudeCLITool({'project_context': '.'})

    # Create agents
    spec_agent = SpecAgent(claude_tool=claude)
    code_agent = CodeAgent(claude_tool=claude)

    # Create orchestrator
    orchestrator = Orchestrator()
    orchestrator.register_agent(spec_agent)
    orchestrator.register_agent(code_agent)

    # Create workflow
    workflow = orchestrator.create_workflow(
        workflow_id="spec_to_code",
        context={'original_requirement': requirement}
    )

    # Add spec step
    spec_task = Task(
        id="spec_1",
        type="spec",
        input=requirement,
        context={'step': 1}
    )
    orchestrator.add_step(workflow, "spec_agent", spec_task)

    # Add code step
    code_task = Task(
        id="code_1",
        type="code",
        input=requirement,
        context={'step': 2}
    )
    orchestrator.add_step(workflow, "code_agent", code_task)

    # Execute workflow
    result = await orchestrator.execute_workflow(workflow)

    print(f"\nWorkflow Status: {result.status.value}")
    print(f"Total Steps: {result.total_steps}")
    print(f"Completed Steps: {result.completed_steps}")

    for step in result.steps:
        print(f"\nStep: {step.agent_name}")
        print(f"Status: {step.status.value}")
        if step.result:
            print(f"Success: {step.result.success}")
            if step.result.output:
                print(f"Output: {step.result.output[:200]}...")

    return result


async def example_debug_workflow(error_description: str):
    """
    Example workflow: Debug an issue.
    """
    print(f"=== Starting Debug Workflow ===")
    print(f"Error: {error_description}")

    # Create Claude CLI tool
    claude = ClaudeCLITool({'project_context': '.'})

    # Create debug agent
    debug_agent = DebugAgent(claude_tool=claude)

    # Create orchestrator
    orchestrator = Orchestrator()
    orchestrator.register_agent(debug_agent)

    # Create workflow
    workflow = orchestrator.create_workflow(
        workflow_id="debug",
        context={'error': error_description}
    )

    # Add debug step
    debug_task = Task(
        id="debug_1",
        type="debug",
        input=error_description
    )
    orchestrator.add_step(workflow, "debug_agent", debug_task)

    # Execute workflow
    result = await orchestrator.execute_workflow(workflow)

    print(f"\nWorkflow Status: {result.status.value}")
    if result.steps and result.steps[0].result:
        print(f"\nAnalysis:\n{result.steps[0].result.output}")

    return result


async def example_test_workflow(scope: str = "all"):
    """
    Example workflow: Run tests.
    """
    print(f"=== Starting Test Workflow ===")
    print(f"Scope: {scope}")

    # Create Claude CLI tool
    claude = ClaudeCLITool({'project_context': '.'})

    # Create test agent
    test_agent = TestAgent(claude_tool=claude)

    # Create orchestrator
    orchestrator = Orchestrator()
    orchestrator.register_agent(test_agent)

    # Create workflow
    workflow = orchestrator.create_workflow(
        workflow_id="test",
        context={'scope': scope}
    )

    # Add test step
    test_task = Task(
        id="test_1",
        type="test",
        input=scope
    )
    orchestrator.add_step(workflow, "test_agent", test_task)

    # Execute workflow
    result = await orchestrator.execute_workflow(workflow)

    print(f"\nWorkflow Status: {result.status.value}")
    if result.steps and result.steps[0].result:
        print(f"\nTest Results:\n{result.steps[0].result.output}")

    return result


async def example_direct_agent_call():
    """
    Example: Direct agent call without orchestrator.
    """
    print(f"=== Direct Agent Call Example ===")

    # Create Claude CLI tool
    claude = ClaudeCLITool({'project_context': '.'})

    # Create agent directly
    code_agent = CodeAgent(claude_tool=claude)

    # Create task
    task = Task(
        id="direct_1",
        type="code",
        input="Create a simple hello world function in Python"
    )

    # Execute directly
    result = code_agent.execute(task)

    print(f"\nSuccess: {result.success}")
    print(f"Output:\n{result.output}")


async def main():
    """Run example workflows."""
    print("\n" + "="*50)
    print("AI DevBot Example Workflows")
    print("="*50 + "\n")

    # Run example - uncomment to test
    # await example_direct_agent_call()
    # await example_spec_to_code_workflow("Create a user authentication system")
    # await example_debug_workflow("Connection refused on port 3000")
    # await example_test_workflow("all")

    print("Example workflows defined. Uncomment to run.")


if __name__ == "__main__":
    asyncio.run(main())
