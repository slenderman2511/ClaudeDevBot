"""
Test Workflows Module

Unit tests for workflow components.
"""

import unittest
from unittest.mock import Mock, patch, AsyncMock
import asyncio

from workflows.command_router import CommandRouter, CommandType, ParsedCommand
from workflows.orchestration import Orchestrator, Workflow, TaskStatus
from workflows.task_planner import TaskPlanner, ExecutionPlan
from agents.base_agent import Task, AgentResult
from agents.spec_agent import SpecAgent


class TestCommandRouter(unittest.TestCase):
    """Tests for CommandRouter."""

    def setUp(self):
        self.router = CommandRouter()

    def test_parse_spec_command(self):
        """Test parsing /spec command."""
        parsed = self.router.parse_command(
            "/spec create user API",
            user_id=123,
            chat_id=456,
            message_id=789
        )
        self.assertEqual(parsed.command_type, CommandType.SPEC)
        self.assertEqual(parsed.arguments, "create user API")

    def test_parse_code_command(self):
        """Test parsing /code command."""
        parsed = self.router.parse_command(
            "/code implement login",
            user_id=123,
            chat_id=456,
            message_id=789
        )
        self.assertEqual(parsed.command_type, CommandType.CODE)
        self.assertEqual(parsed.arguments, "implement login")

    def test_parse_status_command(self):
        """Test parsing /status command."""
        parsed = self.router.parse_command(
            "/status",
            user_id=123,
            chat_id=456,
            message_id=789
        )
        self.assertEqual(parsed.command_type, CommandType.STATUS)
        self.assertEqual(parsed.arguments, "")

    def test_parse_unknown_command(self):
        """Test parsing unknown command."""
        parsed = self.router.parse_command(
            "/unknown command",
            user_id=123,
            chat_id=456,
            message_id=789
        )
        self.assertEqual(parsed.command_type, CommandType.UNKNOWN)

    def test_get_help_text(self):
        """Test help text generation."""
        help_text = self.router.get_help_text()
        self.assertIn("/spec", help_text)
        self.assertIn("/code", help_text)
        self.assertIn("/help", help_text)

    def test_command_mapping(self):
        """Test command mapping."""
        mapping = self.router.get_command_mapping()
        self.assertIn("/spec", mapping)
        self.assertIn("/status", mapping)


class TestTaskPlanner(unittest.TestCase):
    """Tests for TaskPlanner."""

    def setUp(self):
        self.planner = TaskPlanner()

    def test_create_plan_for_spec(self):
        """Test creating plan for spec command."""
        parsed = ParsedCommand(
            command_type=CommandType.SPEC,
            raw_command="/spec create user",
            arguments="create user",
            user_id=123,
            chat_id=456,
            message_id=789
        )
        plan = self.planner.create_plan("plan_1", parsed)
        self.assertEqual(len(plan.steps), 1)
        self.assertEqual(plan.steps[0].agent_name, "spec_agent")

    def test_create_plan_for_code(self):
        """Test creating plan for code command."""
        parsed = ParsedCommand(
            command_type=CommandType.CODE,
            raw_command="/code implement login",
            arguments="implement login",
            user_id=123,
            chat_id=456,
            message_id=789
        )
        plan = self.planner.create_plan("plan_2", parsed)
        self.assertEqual(len(plan.steps), 1)
        self.assertEqual(plan.steps[0].agent_name, "code_agent")

    def test_create_plan_for_status(self):
        """Test creating plan for status command."""
        parsed = ParsedCommand(
            command_type=CommandType.STATUS,
            raw_command="/status",
            arguments="",
            user_id=123,
            chat_id=456,
            message_id=789
        )
        plan = self.planner.create_plan("plan_3", parsed)
        self.assertEqual(len(plan.steps), 0)

    def test_estimate_time(self):
        """Test time estimation."""
        spec_time = self.planner.estimate_time(CommandType.SPEC)
        self.assertGreater(spec_time, 0)


class TestOrchestrator(unittest.TestCase):
    """Tests for Orchestrator."""

    def setUp(self):
        self.orchestrator = Orchestrator()

    def test_register_agent(self):
        """Test agent registration."""
        agent = SpecAgent()
        self.orchestrator.register_agent(agent)
        self.assertEqual(self.orchestrator.get_agent("spec_agent"), agent)

    def test_get_agent_not_found(self):
        """Test getting non-existent agent."""
        agent = self.orchestrator.get_agent("nonexistent")
        self.assertIsNone(agent)

    def test_create_workflow(self):
        """Test workflow creation."""
        workflow = self.orchestrator.create_workflow(
            "wf_1",
            CommandType.SPEC,
            {"context": "test"}
        )
        self.assertEqual(workflow.workflow_id, "wf_1")
        self.assertEqual(workflow.command_type, CommandType.SPEC)

    def test_add_step(self):
        """Test adding workflow step."""
        workflow = self.orchestrator.create_workflow("wf_1", CommandType.SPEC)
        task = Task(id="task_1", type="spec", input="test")
        step = self.orchestrator.add_step(workflow, "spec_agent", task)
        self.assertEqual(len(workflow.steps), 1)
        self.assertEqual(step.agent_name, "spec_agent")

    def test_list_workflows(self):
        """Test listing workflows."""
        self.orchestrator.create_workflow("wf_1", CommandType.SPEC)
        self.orchestrator.create_workflow("wf_2", CommandType.CODE)
        workflows = self.orchestrator.list_workflows()
        self.assertEqual(len(workflows), 2)


class TestOrchestratorAsync(unittest.IsolatedAsyncioTestCase):
    """Async tests for Orchestrator."""

    async def test_execute_workflow(self):
        """Test workflow execution."""
        orchestrator = Orchestrator()
        agent = SpecAgent()
        orchestrator.register_agent(agent)

        workflow = orchestrator.create_workflow("wf_1", CommandType.SPEC)
        task = Task(id="task_1", type="spec", input="test specification")
        orchestrator.add_step(workflow, "spec_agent", task)

        result = await orchestrator.execute_workflow(workflow)
        self.assertEqual(result.status, TaskStatus.COMPLETED)


if __name__ == '__main__':
    unittest.main()
