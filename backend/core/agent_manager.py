"""
OpenHands-style multi-agent system. ManagerAgent delegates to specialized agents.
"""
import logging
from typing import Any
from core.model_orchestrator import orchestrator
from core.sandbox_executor import sandbox

logger = logging.getLogger(__name__)

class ManagerAgent:
    """Receives every task first, classifies, breaks into subtasks, delegates, merges."""
    
    async def run(self, state: dict) -> dict:
        prompt = state["prompt"]
        user_tier = state.get("user_tier", "basic")
        task_type = state.get("task_type", "simple_qa")
        
        # For complex research tasks, use multi-step delegation
        if task_type in ("research_task",):
            return await self._run_multi_step_research(state)
        if task_type == "code_execution":
            return await self._run_code_execution(state)
        if task_type == "browser_task":
            return await self._run_browser_task(state)
        
        # Simple tasks: direct LLM response
        res = await orchestrator.run(task_type, prompt, user_tier=user_tier)
        if res["error"]:
            return {**state, "error": res["error"]}
        tokens = res["input_tokens"] + res["output_tokens"]
        return {
            **state, "result": res["result"],
            "tokens_used": tokens, "credits_used": max(1, tokens // 100),
            "metadata": {**state.get("metadata", {}), "model": res["model_used"], "agent": "direct"}
        }
    
    async def _run_browser_task(self, state: dict) -> dict:
        """Delegate to BrowserAgent."""
        from agents.browser_agent import BrowserAgent
        from agents.screenshot_storage import upload_screenshots
        agent = BrowserAgent(task_id=state["task_id"], user_id=state["user_id"], user_tier=state.get("user_tier","basic"))
        try:
            result = await agent.run(state["prompt"])
            if result.success:
                return {**state, "result": result.result, "error": None, "metadata": {**state.get("metadata",{}), "browser_steps": len(result.steps)}}
            else:
                # Fallback to LLM
                res = await orchestrator.run("simple_qa", state["prompt"], user_tier=state.get("user_tier","basic"))
                return {**state, "result": res.get("result",""), "error": result.error, "metadata": {**state.get("metadata",{}), "browser_fallback": True}}
        finally:
            agent.cleanup()
    
    async def _run_code_execution(self, state: dict) -> dict:
        """Delegate to CodeAgent (E2B sandbox)."""
        prompt = state["prompt"]
        user_tier = state.get("user_tier", "basic")
        try:
            system = "Write Python code to fulfill this request. The code will execute in a safe sandbox. Import all needed libraries. Print output. Save any charts to 'chart.png'."
            code_res = await orchestrator.run("code_execution", prompt, user_tier=user_tier, system_prompt=system)
            if code_res["error"]:
                return {**state, "error": code_res["error"]}
            code = code_res["result"]
            # Extract code from markdown
            if "```python" in code:
                code = code.split("```python")[1].split("```")[0].strip()
            elif "```" in code:
                code = code.split("```")[1].split("```")[0].strip()
            exec_res = await sandbox.execute_code(code)
            if exec_res.get("error"):
                return {**state, "error": exec_res["error"]}
            output = exec_res.get("stdout", "")
            chart_data = None
            for f in exec_res.get("files", []):
                if "chart" in f["name"].lower():
                    chart_data = f["data"]
            return {
                **state,
                "result": output,
                "error": exec_res.get("stderr") or None,
                "metadata": {**state.get("metadata", {}), "code_executed": True, "chart": chart_data, "files": exec_res.get("files", [])}
            }
        except Exception as e:
            return {**state, "error": str(e)}
    
    async def _run_multi_step_research(self, state: dict) -> dict:
        """Multi-step research: search browser → extract → synthesize."""
        from agents.browser_agent import BrowserAgent
        prompt = state["prompt"]
        user_tier = state.get("user_tier", "basic")
        task_id = state["task_id"]
        user_id = state["user_id"]
        
        # Step 1: Decompose research question
        decompose_prompt = f"Break this research request into 2-3 specific search queries:\n\n{prompt}"
        decomp_res = await orchestrator.run("research_task", decompose_prompt, user_tier=user_tier)
        if decomp_res["error"]:
            return {**state, "error": decomp_res["error"]}
        queries = decomp_res["result"].split("\n")
        queries = [q.strip().lstrip("0123456789.-) ") for q in queries if q.strip() and len(q.strip()) > 10][:3]
        
        # Step 2: Execute queries via browser
        results = []
        for q in queries:
            agent = BrowserAgent(task_id=task_id, user_id=user_id, user_tier=user_tier)
            try:
                r = await agent.run(q)
                results.append({"query": q, "result": r.result[:2000] if r.success else "Failed"})
            finally:
                agent.cleanup()
        
        # Step 3: Synthesize into report
        context = "\n\n".join([f"Query: {r['query']}\nResult: {r['result']}" for r in results])
        syn_prompt = f"Synthesize the following research findings into a concise report based on the original request:\n\nOriginal: {prompt}\n\nFindings:\n{context}"
        syn_res = await orchestrator.run("research_task", syn_prompt, user_tier=user_tier)
        if syn_res.get("error"):
            return {**state, "error": syn_res["error"]}
        return {
            **state, "result": syn_res["result"],
            "tokens_used": syn_res.get("input_tokens", 0) + syn_res.get("output_tokens", 0),
            "metadata": {**state.get("metadata", {}), "queries": queries, "sub_results": results, "model": syn_res.get("model_used", "")}
        }

manager = ManagerAgent()