# src/tests/test_agents.py
"""Tests for all agents."""

import pytest
from claudebot.agents.base_agent import AgentContext, AgentResult


class TestAgentValidation:
    """Test that agents validate their inputs correctly."""

    @pytest.mark.asyncio
    async def test_spec_agent_requires_description(self, agent_context):
        from claudebot.agents.spec_agent import SpecAgent

        agent = SpecAgent()
        is_valid, error = agent.validate_input({})
        assert is_valid is False
        assert "description" in error.lower()

    @pytest.mark.asyncio
    async def test_spec_agent_accepts_description(self, agent_context):
        from claudebot.agents.spec_agent import SpecAgent

        agent = SpecAgent()
        is_valid, error = agent.validate_input({"description": "Add user auth"})
        assert is_valid is True
        assert error is None

    @pytest.mark.asyncio
    async def test_code_agent_requires_description(self, agent_context):
        from claudebot.agents.code_agent import CodeAgent

        agent = CodeAgent()
        is_valid, error = agent.validate_input({})
        assert is_valid is False
        assert "description" in error.lower()

    @pytest.mark.asyncio
    async def test_test_agent_requires_files_or_description(self, agent_context):
        from claudebot.agents.test_agent import TestAgent

        agent = TestAgent()
        is_valid, error = agent.validate_input({})
        assert is_valid is False

        # Either description or files should be valid
        is_valid, _ = agent.validate_input({"description": "test something"})
        assert is_valid is True
        is_valid, _ = agent.validate_input({"files": ["src/main.py"]})
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_debug_agent_name(self, agent_context):
        from claudebot.agents.debug_agent import DebugAgent

        agent = DebugAgent()
        assert agent.name == "debug"
        assert agent.description != ""

    @pytest.mark.asyncio
    async def test_deploy_agent_name(self, agent_context):
        from claudebot.agents.deploy_agent import DeployAgent

        agent = DeployAgent()
        assert agent.name == "deploy"
        assert agent.description != ""

    @pytest.mark.asyncio
    async def test_planner_agent_name(self, agent_context):
        from claudebot.agents.planner_agent import PlannerAgent

        agent = PlannerAgent()
        assert agent.name == "planner"
        assert agent.description != ""

    @pytest.mark.asyncio
    async def test_planner_agent_requires_feature_name(self, agent_context):
        from claudebot.agents.planner_agent import PlannerAgent

        agent = PlannerAgent()
        is_valid, error = agent.validate_input({})
        assert is_valid is False
        assert "feature name" in error.lower() or "description" in error.lower()


class TestAgentErrors:
    """Test that agents return proper AgentResult on error."""

    @pytest.mark.asyncio
    async def test_spec_agent_handles_missing_api_key(self, agent_context):
        from claudebot.agents.spec_agent import SpecAgent

        # Create context with empty API key to trigger error path
        bad_context = AgentContext(
            repo_path=agent_context.repo_path,
            branch="main",
            claude_api_key="",  # Empty key
            config={},
        )

        agent = SpecAgent()
        # Should return error result (not raise)
        result = await agent.execute(
            {"description": "test"},
            bad_context,
        )
        assert isinstance(result, AgentResult)
        assert result.success is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_code_agent_returns_error_on_empty_description(self, agent_context):
        from claudebot.agents.code_agent import CodeAgent

        agent = CodeAgent()
        result = await agent.execute({}, agent_context)
        assert result.success is False
        assert "description" in result.summary.lower()

    @pytest.mark.asyncio
    async def test_test_agent_returns_error_when_no_files(self, agent_context):
        from claudebot.agents.test_agent import TestAgent

        agent = TestAgent()
        result = await agent.execute(
            {"description": ""},
            agent_context,
        )
        assert result.success is False

    @pytest.mark.asyncio
    async def test_planner_agent_handles_missing_openspec(self, agent_context):
        from claudebot.agents.planner_agent import PlannerAgent

        agent = PlannerAgent(openspec=None)  # No OpenSpec
        result = await agent.execute(
            {"description": "some-feature"},
            agent_context,
        )
        assert result.success is False
        assert "openspec" in result.error.lower() or "openspec" in result.summary.lower()


class TestTestAgentParsing:
    """Test TestAgent output parsing."""

    def test_detect_language_python(self):
        from claudebot.agents.test_agent import TestAgent

        agent = TestAgent()
        lang = agent._detect_language(["src/main.py", "src/utils.py"])
        assert lang == "python"

    def test_detect_language_javascript(self):
        from claudebot.agents.test_agent import TestAgent

        agent = TestAgent()
        lang = agent._detect_language(["src/app.js", "src/index.js"])
        assert lang == "javascript"

    def test_detect_language_typescript(self):
        from claudebot.agents.test_agent import TestAgent

        agent = TestAgent()
        lang = agent._detect_language(["src/app.ts", "src/index.tsx"])
        assert lang == "typescript"

    def test_detect_language_defaults_to_python(self):
        from claudebot.agents.test_agent import TestAgent

        agent = TestAgent()
        lang = agent._detect_language(["README.md"])
        assert lang == "python"

    def test_parse_test_output_single_file(self):
        from claudebot.agents.test_agent import TestAgent

        agent = TestAgent()
        output = "---FILE:test_main.py---\nimport pytest\n\ndef test_example():\n    assert True\n"
        files = agent._parse_test_output(output, "/tmp", "python")
        assert "test_main.py" in files

    def test_parse_test_output_multiple_files(self):
        from claudebot.agents.test_agent import TestAgent

        agent = TestAgent()
        output = (
            "---FILE:tests/test_a.py---\nimport pytest\n\ndef test_a():\n    pass\n"
            "---FILE:tests/test_b.py---\nimport pytest\n\ndef test_b():\n    pass\n"
        )
        files = agent._parse_test_output(output, "/tmp", "python")
        assert "tests/test_a.py" in files
        assert "tests/test_b.py" in files


class TestTaskGraph:
    """Test TaskGraph data structures."""

    def test_task_graph_add_task(self):
        from claudebot.agents.planner_agent import TaskGraph, TaskNode

        graph = TaskGraph("test-feature")
        node = TaskNode("task_0", "Write spec", "Design", [])
        graph.add_task(node)
        assert "task_0" in graph.nodes
        assert graph.nodes["task_0"].name == "Write spec"

    def test_task_graph_infer_agent_type(self):
        from claudebot.agents.planner_agent import TaskNode

        spec_node = TaskNode("t1", "Design spec", "Design", [])
        assert spec_node.agent_type == "spec"

        impl_node = TaskNode("t2", "Implement feature", "Implementation", [])
        assert impl_node.agent_type == "code"

        test_node = TaskNode("t3", "Write tests", "Testing", [])
        assert test_node.agent_type == "test"

        deploy_node = TaskNode("t4", "Deploy to prod", "Deployment", [])
        assert deploy_node.agent_type == "deploy"

    def test_task_graph_topological_sort(self):
        from claudebot.agents.planner_agent import TaskGraph, TaskNode

        graph = TaskGraph("test-feature")
        # Phase 1 tasks
        graph.add_task(TaskNode("t1", "Write spec", "Design", []))
        # Phase 2 tasks (depend on t1)
        graph.add_task(TaskNode("t2", "Implement", "Implementation", ["t1"]))
        graph.add_task(TaskNode("t3", "Write tests", "Testing", ["t1"]))

        levels = graph.topological_sort()
        assert len(levels) == 2
        # First level: t1 only
        assert [n.task_id for n in levels[0]] == ["t1"]
        # Second level: t2 and t3 (can run in parallel)
        assert set(n.task_id for n in levels[1]) == {"t2", "t3"}

    def test_task_graph_get_ready_tasks(self):
        from claudebot.agents.planner_agent import TaskGraph, TaskNode

        graph = TaskGraph("test-feature")
        graph.add_task(TaskNode("t1", "First", "Design", []))
        graph.add_task(TaskNode("t2", "Second", "Implementation", ["t1"]))

        ready = graph.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].task_id == "t1"
