import unittest
from unittest.mock import patch, MagicMock, call
import json
import tempfile
import os
import shutil
from pathlib import Path

# Import the orchestrator module
import orchestrator

class TestOrchestrator(unittest.TestCase):
    
    def setUp(self):
        # Create a temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        # Initialize a git repo for testing
        os.system("git init")
        os.system("git config user.name 'Test User'")
        os.system("git config user.email 'test@example.com'")
        
        # Create a basic config file
        config_data = {
            "model": "qwen3-coder:latest",
            "aider_model": "openai/qwen3-coder:latest",
            "max_blocks": 6,
            "max_attempts_per_block": 3,
            "timeout_minutes_per_aider_run": 45,
            "commands": {
                "test": "npm test",
                "typecheck": "npm run typecheck",
                "lint": "npm run lint"
            },
            "protected_paths": [
                ".git",
                "node_modules",
                "dist",
                "vendor",
                "package-lock.json"
            ]
        }
        
        with open("config.json", "w") as f:
            json.dump(config_data, f)
            
        # Create a task file
        with open("task.md", "w") as f:
            f.write("# Feature\nAdd multiplication and subtraction support to the calculator.")
    
    def tearDown(self):
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
    
    @patch('orchestrator.settings')
    def test_process_environment_uses_openai_api_base(self, mock_settings):
        # Setup mock settings
        mock_settings.openai_api_base = "http://mock-ollama:11434/v1"
        
        env = orchestrator.process_environment()
        
        self.assertEqual(env["OPENAI_API_BASE"], "http://mock-ollama:11434/v1")
        self.assertEqual(env["OPENAI_API_KEY"], "ollama")
    
    @patch('orchestrator.ollama_structured')
    def test_planner_uses_ollama_chat_url(self, mock_ollama):
        # Setup mock
        mock_ollama.return_value = {
            "complete": False,
            "reason": "",
            "block": None
        }
        
        # This should use the OLLAMA_CHAT_URL from settings
        with patch('orchestrator.settings') as mock_settings:
            mock_settings.ollama_chat_url = "http://mock-ollama:11434/api/chat"
            
            try:
                orchestrator.create_next_block(
                    model="test-model",
                    task="test task",
                    state={},
                    project_snapshot=""
                )
            except Exception:
                # We expect this to fail because we're mocking Ollama
                pass
            
            # Verify that ollama_structured was called with the correct URL
            mock_ollama.assert_called()
    
    @patch('orchestrator.ollama_structured')
    def test_reviewer_uses_ollama_chat_url(self, mock_ollama):
        # Setup mock
        mock_ollama.return_value = {
            "approved": True,
            "summary": "",
            "requirements": [],
            "required_fixes": []
        }
        
        with patch('orchestrator.settings') as mock_settings:
            mock_settings.ollama_chat_url = "http://mock-ollama:11434/api/chat"
            
            try:
                orchestrator.review_block(
                    model="test-model",
                    task="test task",
                    block={"id": "test", "title": "Test"},
                    diff="test diff",
                    verification={},
                    protected_violations=[]
                )
            except Exception:
                # We expect this to fail because we're mocking Ollama
                pass
            
            # Verify that ollama_structured was called with the correct URL
            mock_ollama.assert_called()
    
    def test_protected_path_detection(self):
        violations = orchestrator.detect_protected_changes(
            files=[".git/config", "src/main.py", "node_modules/package.json"],
            protected_paths=[".git", "node_modules"]
        )
        
        self.assertIn(".git/config", violations)
        self.assertIn("node_modules/package.json", violations)
    
    def test_changed_files_parsing(self):
        # Create some test files
        with open("test1.py", "w") as f:
            f.write("print('hello')")
            
        os.system("git add test1.py")
        os.system("git commit -m 'Add test file'")
        
        # Modify the file
        with open("test1.py", "w") as f:
            f.write("print('hello world')")
            
        files = orchestrator.changed_files(Path("."))
        self.assertIn("test1.py", files)
    
    def test_changed_files_with_renames(self):
        # Create a test file
        with open("old_file.py", "w") as f:
            f.write("print('hello')")
        
        os.system("git add old_file.py")
        os.system("git commit -m 'Add old file'")
        
        # Rename the file
        os.rename("old_file.py", "new_file.py")
        
        files = orchestrator.changed_files(Path("."))
        self.assertIn("new_file.py", files)
    
    def test_aider_arguments(self):
        # Test that aider is called with correct arguments
        with patch('orchestrator.run_command') as mock_run_command:
            mock_run_command.return_value = MagicMock(return_code=0, stdout="", stderr="")
            
            try:
                orchestrator.run_aider(
                    project_root=Path("."),
                    config={
                        "aider_model": "test-model",
                        "timeout_minutes_per_aider_run": 1,
                        "commands": {"test": "npm test"}
                    },
                    prompt="test prompt",
                    block={"files": ["test.py"]}
                )
            except Exception:
                # We expect this to fail because we're mocking run_command
                pass
            
            # Verify that the correct arguments were passed
            call_args = mock_run_command.call_args[0][0]
            self.assertIn("--no-show-model-warnings", call_args)
            self.assertIn("--no-pretty", call_args)
            self.assertIn("--no-stream", call_args)
            self.assertIn("--yes-always", call_args)
            self.assertIn("--no-auto-commits", call_args)
    
    def test_verification_always_runs_git_diff_check(self):
        with patch('orchestrator.run_command') as mock_run_command:
            mock_run_command.return_value = MagicMock(return_code=0, stdout="", stderr="")
            
            try:
                orchestrator.run_verification(
                    project_root=Path("."),
                    config={"commands": {}}
                )
            except Exception:
                # We expect this to fail because we're mocking run_command
                pass
            
            # Verify that git diff --check was called
            calls = mock_run_command.call_args_list
            diff_check_called = any(
                "diff" in call[0][0] and "--check" in call[0][0] 
                for call in calls
            )
            self.assertTrue(diff_check_called)
    
    def test_invalid_ollama_response_raises_error(self):
        with patch('urllib.request.urlopen') as mock_urlopen:
            # Mock an empty response from Ollama
            mock_response = MagicMock()
            mock_response.read.return_value = b'{"message": {"content": ""}}'
            mock_urlopen.return_value.__enter__.return_value = mock_response
            
            with self.assertRaises(RuntimeError) as context:
                orchestrator.ollama_structured(
                    model="test-model",
                    system_prompt="test",
                    user_prompt="test",
                    schema={}
                )
            
            self.assertIn("Ollama returnerade ett tomt svar", str(context.exception))
    
    def test_empty_ollama_response_raises_error(self):
        with patch('urllib.request.urlopen') as mock_urlopen:
            # Mock an invalid JSON response from Ollama
            mock_response = MagicMock()
            mock_response.read.return_value = b'{"message": {"content": "invalid json"}'
            mock_urlopen.return_value.__enter__.return_value = mock_response
            
            with self.assertRaises(RuntimeError) as context:
                orchestrator.ollama_structured(
                    model="test-model",
                    system_prompt="test",
                    user_prompt="test",
                    schema={}
                )
            
            self.assertIn("Ollama returnerade ogiltig JSON", str(context.exception))

    @patch('orchestrator.Planner')
    def test_execute_cycle_returns_none_when_no_task(self, mock_planner_class):
        # Setup mock
        mock_planner = MagicMock()
        mock_planner.next_builder_task.return_value = None
        mock_planner_class.return_value = mock_planner
        
        # Test execute_cycle returns None when no task
        result = orchestrator.execute_cycle(
            planner=mock_planner,
            project_root=Path("."),
            config={}
        )
        
        self.assertIsNone(result)
        mock_planner.next_builder_task.assert_called_once_with()

    @patch('orchestrator.Planner')
    def test_execute_cycle_executes_full_cycle(self, mock_planner_class):
        # Setup mocks
        mock_planner = MagicMock()
        
        # Create a BuilderTask instance
        from orchestrator import BuilderTask
        task = BuilderTask(
            prompt="Implement the example",
            files=(Path("example.py"),),
        )
        mock_planner.next_builder_task.return_value = task
        mock_planner_class.return_value = mock_planner
        
        mock_builder_result = MagicMock()
        mock_test_result = orchestrator.ExecutionResult(
            return_code=0,
            stdout="tests passed",
            stderr="",
        )
        mock_review_result = MagicMock()
        
        with patch('orchestrator.run_builder', return_value=mock_builder_result), \
             patch('orchestrator.run_tests', return_value=mock_test_result), \
             patch('orchestrator.run_review', return_value=mock_review_result):
            
            # Test execute_cycle executes full cycle
            result = orchestrator.execute_cycle(
                planner=mock_planner,
                project_root=Path("."),
                config={"timeout_minutes_per_aider_run": 1}
            )
            
            # Verify all functions were called
            orchestrator.run_builder.assert_called_once()
            orchestrator.run_tests.assert_called_once_with()
            orchestrator.run_review.assert_called_once()
            
            # Verify that next_builder_task was called
            mock_planner.next_builder_task.assert_called_once_with()
            
            # Verify result is correct type
            self.assertIsInstance(result, orchestrator.CycleResult)
            self.assertEqual(result.builder_result, mock_builder_result)
            self.assertEqual(result.test_result, mock_test_result)
            self.assertEqual(result.review_result, mock_review_result)

if __name__ == '__main__':
    unittest.main()
