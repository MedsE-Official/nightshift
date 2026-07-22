from __future__ import annotations

from aider_workflow import build_aider_prompt, run_aider, run_verification, write_report
from architect import ARCHITECTURE_SCHEMA, create_architecture_contract
from contracts import ArchitectureContract, contract_change_violations
from autonomous_orchestrator import CONFIG_PATH, REPORT_DIR, STATE_DIR, STATE_PATH, TASK_PATH, main, parse_args
from builder import Builder, BuilderResult, BuilderTask, run_builder
from cycle_execution import CycleResult, execute_all_tasks, execute_backlog, execute_cycle, execute_next_task
from git_tools import changed_files, detect_protected_changes, git_checkpoint, git_get_changes_since_commit, git_restore_checkpoint, git_review_bundle, git_status
from ollama_workflow import OLLAMA_CHAT_URL, PLAN_SCHEMA, REVIEW_SCHEMA, create_next_block, ollama_structured, review_block
from orchestrator_runtime import CommandResult, load_json, process_environment, run_command, run_shell_command, save_json, settings
from planner import Planner
from review import Reviewer, ReviewResult, run_review
from test_runner import ExecutionResult, run_tests

if __name__ == "__main__":
    raise SystemExit(main())
