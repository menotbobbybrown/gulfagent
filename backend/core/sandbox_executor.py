"""
E2B code interpreter sandbox for secure code execution.
All user-provided code runs in isolated E2B sandbox — never on host.
"""
import asyncio, base64, logging, os
from typing import Any
from e2b_code_interpreter import Sandbox
from config import get_settings

logger = logging.getLogger(__name__)

class SandboxExecutor:
    def __init__(self):
        self.api_key = get_settings().e2b_api_key
    
    async def execute_code(self, code: str, language: str = "python") -> dict:
        """Execute code in isolated E2B sandbox. Timeout 30s."""
        if not self.api_key:
            return {"stdout": "", "stderr": "E2B_API_KEY not configured", "files": [], "error": "E2B_API_KEY missing"}
        loop = asyncio.get_event_loop()
        try:
            def _run():
                with Sandbox(api_key=self.api_key) as sbx:
                    result = sbx.run_code(code, language=language)
                    files = []
                    if result.files:
                        for f in result.files:
                            files.append({"name": f.name, "data": base64.b64encode(f.read_bytes()).decode()})
                    return {"stdout": result.text, "stderr": result.error or "", "files": files, "error": None}
            res = await asyncio.wait_for(loop.run_in_executor(None, _run), timeout=30)
            return res
        except asyncio.TimeoutError:
            return {"stdout": "", "stderr": "Execution timed out after 30s", "files": [], "error": "TIMEOUT"}
        except Exception as e:
            return {"stdout": "", "stderr": str(e), "files": [], "error": str(e)}

    async def execute_with_files(self, code: str, files: list, language: str = "python") -> dict:
        """Execute code with uploaded files in sandbox."""
        if not self.api_key:
            return {"stdout": "", "stderr": "E2B_API_KEY not configured", "files": [], "error": "E2B_API_KEY missing"}
        loop = asyncio.get_event_loop()
        try:
            def _run():
                with Sandbox(api_key=self.api_key) as sbx:
                    uploaded = []
                    for f in files:
                        fpath = f"/tmp/{f['name']}"
                        sbx.files.write(fpath, base64.b64decode(f['data']) if 'data' in f else f['content'])
                        uploaded.append(fpath)
                    result = sbx.run_code(code, language=language)
                    out_files = []
                    if result.files:
                        for f in result.files:
                            out_files.append({"name": f.name, "data": base64.b64encode(f.read_bytes()).decode()})
                    return {"stdout": result.text, "stderr": result.error or "", "files": out_files, "error": None}
            return await asyncio.wait_for(loop.run_in_executor(None, _run), timeout=30)
        except Exception as e:
            return {"stdout": "", "stderr": str(e), "files": [], "error": str(e)}

    async def execute_data_analysis(self, file_data: dict, prompt: str, user_tier: str = "basic") -> dict:
        """Upload file, have Kimi K2 write analysis code, execute it, return results."""
        from core.model_orchestrator import orchestrator
        system = "Write Python code using pandas/matplotlib to analyze this data. The code will run in an E2B sandbox. Import pandas, matplotlib, seaborn. Save any charts to 'chart.png'. Print results."
        code_res = await orchestrator.run("code_execution", prompt, user_tier=user_tier, system_prompt=system)
        if code_res["error"]:
            return {"error": code_res["error"]}
        code = code_res["result"]
        # Strip markdown code blocks if present
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0].strip()
        elif "```" in code:
            code = code.split("```")[1].split("```")[0].strip()
        exec_res = await self.execute_with_files(code, [file_data])
        return {**exec_res, "code_written": code}

sandbox = SandboxExecutor()