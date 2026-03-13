"""
Test Agents Module

Unit tests for agent implementations.
"""

import unittest
from unittest.mock import Mock, patch
import time

from agents.base_agent import BaseAgent, Task, AgentResult
from agents.spec_agent import SpecAgent
from agents.code_agent import CodeAgent
from agents.test_agent import TestAgent
from agents.deploy_agent import DeployAgent
from agents.debug_agent import DebugAgent


class TestBaseAgent(unittest.TestCase):
    """Tests for BaseAgent class."""

    def test_agent_initialization(self):
        """Test agent initialization."""
        agent = SpecAgent()
        self.assertEqual(agent.name, "spec_agent")
        self.assertEqual(agent.model, "sonnet")
        self.assertEqual(agent.max_iterations, 10)

    def test_validate_input_valid(self):
        """Test input validation with valid input."""
        agent = SpecAgent()
        self.assertTrue(agent.validate_input("valid input"))

    def test_validate_input_empty(self):
        """Test input validation with empty input."""
        agent = SpecAgent()
        self.assertFalse(agent.validate_input(""))

    def test_validate_input_whitespace(self):
        """Test input validation with whitespace only."""
        agent = SpecAgent()
        self.assertFalse(agent.validate_input("   "))

    def test_get_capabilities(self):
        """Test getting agent capabilities."""
        agent = SpecAgent()
        capabilities = agent.get_capabilities()
        self.assertIsInstance(capabilities, list)

    def test_get_config(self):
        """Test getting agent config."""
        agent = SpecAgent({'custom_key': 'custom_value'})
        config = agent.get_config()
        self.assertEqual(config['name'], 'spec_agent')
        self.assertIn('model', config)


class TestSpecAgent(unittest.TestCase):
    """Tests for SpecAgent."""

    def test_spec_agent_execute(self):
        """Test spec agent execution."""
        agent = SpecAgent()
        task = Task(id="test_1", type="spec", input="Create a user authentication system")
        result = agent.execute(task)
        self.assertTrue(result.success)
        self.assertIn("specification", result.output.lower())

    def test_spec_agent_invalid_input(self):
        """Test spec agent with invalid input."""
        agent = SpecAgent()
        task = Task(id="test_2", type="spec", input="")
        result = agent.execute(task)
        self.assertFalse(result.success)
        self.assertIsNotNone(result.error)


class TestCodeAgent(unittest.TestCase):
    """Tests for CodeAgent."""

    def test_code_agent_execute(self):
        """Test code agent execution."""
        agent = CodeAgent()
        task = Task(id="test_1", type="code", input="Create a REST API endpoint")
        result = agent.execute(task)
        self.assertTrue(result.success)

    def test_code_agent_capabilities(self):
        """Test code agent capabilities."""
        agent = CodeAgent()
        capabilities = agent.get_capabilities()
        self.assertIn("generate_python", capabilities)


class TestTestAgent(unittest.TestCase):
    """Tests for TestAgent."""

    def test_test_agent_execute(self):
        """Test test agent execution."""
        agent = TestAgent()
        task = Task(id="test_1", type="test", input="Run all tests")
        result = agent.execute(task)
        self.assertTrue(result.success)


class TestDeployAgent(unittest.TestCase):
    """Tests for DeployAgent."""

    def test_deploy_agent_execute(self):
        """Test deploy agent execution."""
        agent = DeployAgent()
        task = Task(id="test_1", type="deploy", input="production")
        result = agent.execute(task)
        self.assertTrue(result.success)


class TestDebugAgent(unittest.TestCase):
    """Tests for DebugAgent."""

    def test_debug_agent_execute(self):
        """Test debug agent execution."""
        agent = DebugAgent()
        task = Task(id="test_1", type="debug", input="Connection refused error")
        result = agent.execute(task)
        self.assertTrue(result.success)


if __name__ == '__main__':
    unittest.main()
