"""
AgentBrain — The LLM Execution Loop

Given an agent config + task + room context, runs a ReAct loop:
  1. Build prompt  (system + context + task)
  2. Call LLM
  3. If tool call → execute → feed result back
  4. Repeat until done (no more tool calls) or MAX_STEPS reached
  5. Return structured result dict
"""

import json
import logging
from typing import Dict, Any, List
from datetime import datetime

from llm_provider import get_llm
from mcp_registry  import get_tool, get_schemas_for_capabilities, get_all_schemas

logger    = logging.getLogger(__name__)
MAX_STEPS = 12   # prevent infinite loops


class AgentBrain:

    def __init__(self, agent_config: Dict[str, Any]):
        """
        agent_config keys:
          id, name, role, system_prompt (optional), capabilities (list),
          config (dict with optional: temperature, max_tokens)
        """
        self.agent = agent_config
        self.llm   = get_llm()

    # ------------------------------------------------------------------ #
    # Public                                                               #
    # ------------------------------------------------------------------ #

    async def run(
        self,
        task:         Dict[str, Any],
        room_context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Execute a task. Returns:
          {status, output, steps, tool_results, completed_at}
        """
        room_context  = room_context or {}
        capabilities  = self.agent.get("capabilities", [])

        # Use all registered tools if no specific capabilities listed
        if capabilities:
            tool_schemas = get_schemas_for_capabilities(capabilities)
        else:
            tool_schemas = get_all_schemas()

        messages = self._build_initial_messages(task, room_context)
        steps_taken   = 0
        tool_log      = []
        last_content  = ""

        while steps_taken < MAX_STEPS:
            steps_taken += 1
            logger.info(f"[{self.agent['name']}] Step {steps_taken}/{MAX_STEPS}")

            try:
                response = await self.llm.complete(
                    messages    = messages,
                    tools       = tool_schemas or None,
                    temperature = self.agent.get("config", {}).get("temperature", 0.7),
                    max_tokens  = self.agent.get("config", {}).get("max_tokens", 2048),
                )
            except Exception as e:
                logger.error(f"LLM call failed: {e}")
                return self._result("error", f"LLM call failed: {e}", steps_taken, tool_log)

            last_content = response.content

            # ---- No tool calls → agent is done ----
            if not response.tool_calls:
                logger.info(f"[{self.agent['name']}] Done after {steps_taken} steps.")
                return self._result("completed", last_content, steps_taken, tool_log)

            # ---- Append assistant turn ----
            messages.append({
                "role":       "assistant",
                "content":    response.content or "",
                "tool_calls": [
                    {
                        "id":       tc["id"],
                        "type":     "function",
                        "function": {
                            "name":      tc["name"],
                            "arguments": json.dumps(tc["arguments"]),
                        },
                    }
                    for tc in response.tool_calls
                ],
            })

            # ---- Execute each tool call ----
            for tc in response.tool_calls:
                tool_name = tc["name"]
                tool_args = tc["arguments"]

                # Inject execution context
                tool_args["_agent_id"] = str(self.agent.get("id", ""))
                tool_args["_task_id"]  = str(task.get("id", ""))
                tool_args["_room_id"]  = str(task.get("room_id", ""))

                tool_entry = get_tool(tool_name)
                if tool_entry:
                    try:
                        result = await tool_entry["fn"](**tool_args)
                        result_str = json.dumps(result) if not isinstance(result, str) else result
                        logger.info(f"[{self.agent['name']}] Tool '{tool_name}' OK")
                    except Exception as e:
                        result_str = json.dumps({"error": str(e)})
                        logger.warning(f"[{self.agent['name']}] Tool '{tool_name}' error: {e}")
                else:
                    result_str = json.dumps({"error": f"Tool '{tool_name}' not registered"})

                tool_log.append({"tool": tool_name, "result": result_str})
                messages.append({
                    "role":         "tool",
                    "tool_call_id": tc["id"],
                    "content":      result_str,
                })

        # Max steps reached
        logger.warning(f"[{self.agent['name']}] Max steps reached.")
        return self._result("max_steps", last_content, steps_taken, tool_log)

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    def _build_initial_messages(self, task: Dict, room_context: Dict) -> List[Dict]:
        system_prompt = self.agent.get(
            "system_prompt",
            f"You are a {self.agent.get('role', 'specialist')} AI agent. "
            f"Your name is {self.agent.get('name', 'Agent')}. "
            f"Complete your assigned tasks thoroughly and report your results."
        )

        context_block = ""
        if room_context:
            context_block = f"\n\n## Shared Room Context (Blackboard):\n{json.dumps(room_context, indent=2)}"

        task_input = task.get("payload", task.get("input_payload", {}))
        task_block = (
            f"\n\n## Your Task:\n"
            f"**Title:** {task.get('title', task.get('task_type', 'Task'))}\n"
            f"**Type:** {task.get('task_type', 'general')}\n"
            f"**Input Data:**\n{json.dumps(task_input, indent=2)}\n\n"
            f"Use your tools when you need to search, fetch data, or take action. "
            f"Always broadcast important findings to the room. "
            f"When you are finished, provide a clear summary of what you accomplished."
        )

        return [
            {"role": "system", "content": system_prompt + context_block + task_block},
            {"role": "user",   "content": f"Please begin working on your task: {task.get('title', 'Task')}"},
        ]

    @staticmethod
    def _result(status: str, output: str, steps: int, tool_log: list) -> Dict:
        return {
            "status":       status,
            "output":       output,
            "steps":        steps,
            "tool_results": tool_log,
            "completed_at": datetime.utcnow().isoformat(),
        }
