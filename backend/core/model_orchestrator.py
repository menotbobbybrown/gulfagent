import time
import asyncio
from typing import Dict, Any, Optional, List
from openai import OpenAI
from config import get_settings

settings = get_settings()

client = OpenAI(
    base_url=settings.openrouter_base_url,
    api_key=settings.openrouter_api_key,
    default_headers={
        "HTTP-Referer": settings.openrouter_site_url,
        "X-Title": settings.openrouter_app_name,
    }
)

MODEL_ROUTES = {
    "simple_qa": {
        "primary": "google/gemini-flash-1.5",
        "secondary": "google/gemini-flash-1.5",
        "emergency": "google/gemini-flash-1.5",
        "cost_per_1k_in": 0.000075,
        "cost_per_1k_out": 0.0003,
    },
    "browser_task": {
        "primary": "moonshotai/kimi-k2.6",
        "secondary": "google/gemini-flash-1.5",
        "emergency": "google/gemini-flash-1.5",
        "cost_per_1k_in": 0.0009,
        "cost_per_1k_out": 0.0036,
    },
    "arabic_task": {
        "primary": "mistralai/mistral-large",
        "secondary": "google/gemini-flash-1.5",
        "emergency": "google/gemini-flash-1.5",
        "cost_per_1k_in": 0.002,
        "cost_per_1k_out": 0.008,
    },
    "code_task": {
        "primary": "moonshotai/kimi-k2.6",
        "secondary": "google/gemini-flash-1.5",
        "emergency": "google/gemini-flash-1.5",
        "cost_per_1k_in": 0.0009,
        "cost_per_1k_out": 0.0036,
    },
    "research_task": {
        "primary": "google/gemini-pro-1.5",
        "secondary": "google/gemini-flash-1.5",
        "emergency": "google/gemini-flash-1.5",
        "cost_per_1k_in": 0.0025,
        "cost_per_1k_out": 0.0075,
    },
    "creative_task": {
        "primary": "meta-llama/llama-3.3-70b",
        "secondary": "google/gemini-flash-1.5",
        "emergency": "google/gemini-flash-1.5",
        "cost_per_1k_in": 0.0006,
        "cost_per_1k_out": 0.002,
    },
    "sensitive_task": {
        "primary": "mistralai/mistral-large",
        "secondary": "google/gemini-flash-1.5",
        "emergency": "google/gemini-flash-1.5",
        "cost_per_1k_in": 0.002,
        "cost_per_1k_out": 0.008,
    },
    "classifier": {
        "primary": "moonshotai/kimi-k2.6:free",
        "secondary": "google/gemini-flash-1.5",
        "emergency": "google/gemini-flash-1.5",
        "cost_per_1k_in": 0.0,
        "cost_per_1k_out": 0.0,
    },
    "connector_format": {
        "primary": "google/gemini-flash-1.5",
        "secondary": "google/gemini-flash-1.5",
        "emergency": "google/gemini-flash-1.5",
        "cost_per_1k_in": 0.000075,
        "cost_per_1k_out": 0.0003,
    },
}

class ModelOrchestrator:
    def __init__(self):
        self.usage_log = []

    async def run(
        self, 
        task_type: str, 
        prompt: str, 
        user_tier: str = "basic", 
        system_prompt: str = "", 
        task_id: str = None
    ) -> dict:
        route = MODEL_ROUTES.get(task_type, MODEL_ROUTES["simple_qa"])
        
        # Cost optimizer for basic tier
        models_to_try = [route["primary"], route["secondary"], route["emergency"]]
        if user_tier == "basic" and task_type not in ["sensitive_task", "browser_task", "arabic_task"]:
            # Prefer gemini-flash for basic tier
            models_to_try = ["google/gemini-flash-1.5", route["primary"], route["emergency"]]

        # Prepend context
        final_prompt = prompt
        if task_type == "arabic_task":
            final_prompt = f"Context: GCC cultural nuances apply. Respond in appropriate Arabic dialect or MSA as requested.\n\n{prompt}"
        
        # Trim prompt (simplistic trim for now)
        max_chars = 100000 * 4 # roughly 100k tokens
        if len(final_prompt) > max_chars:
            final_prompt = final_prompt[:max_chars]

        fallback_used = False
        last_error = None
        
        for i, model in enumerate(models_to_try):
            if i > 0:
                fallback_used = True
            
            start_time = time.time()
            try:
                # Use asyncio.to_thread for synchronous OpenAI client
                response = await asyncio.to_thread(
                    client.chat.completions.create,
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": final_prompt}
                    ],
                    temperature=0.7 if task_type == "creative_task" else 0,
                )
                
                latency_ms = int((time.time() - start_time) * 1000)
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens
                
                # Calculate cost
                # Note: This is an approximation based on the route's cost, 
                # might be slightly off if fallback to a model with different cost.
                # For accuracy, we'd need a model -> cost map.
                in_cost = (input_tokens / 1000) * route["cost_per_1k_in"]
                out_cost = (output_tokens / 1000) * route["cost_per_1k_out"]
                cost_usd = in_cost + out_cost
                
                result = {
                    "result": response.choices[0].message.content,
                    "model_used": model,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cost_usd": cost_usd,
                    "latency_ms": latency_ms,
                    "fallback_used": fallback_used,
                    "error": None
                }
                
                self._log_usage(result)
                return result

            except Exception as e:
                last_error = str(e)
                continue
        
        return {
            "result": "",
            "model_used": "",
            "input_tokens": 0,
            "output_tokens": 0,
            "cost_usd": 0,
            "latency_ms": 0,
            "fallback_used": fallback_used,
            "error": last_error or "All models failed"
        }

    async def classify(self, prompt: str, language: str = "en") -> str:
        system_prompt = (
            "Classify the following user prompt into one of these types: "
            "simple_qa, browser_task, arabic_task, code_task, research_task, creative_task, sensitive_task. "
            "Return ONLY the type name."
        )
        
        res = await self.run("classifier", prompt, system_prompt=system_prompt)
        classification = res["result"].strip().lower()
        
        valid_types = [
            "simple_qa", "browser_task", "arabic_task", "code_task", 
            "research_task", "creative_task", "sensitive_task"
        ]
        
        for t in valid_types:
            if t in classification:
                return t
        
        return "simple_qa"

    def _log_usage(self, result: dict):
        self.usage_log.append({
            "timestamp": time.time(),
            "model_used": result["model_used"],
            "cost_usd": result["cost_usd"],
            "latency_ms": result["latency_ms"],
            "fallback_used": result["fallback_used"]
        })

    def get_cost_today(self) -> float:
        now = time.time()
        one_day_ago = now - 86400
        return sum(log["cost_usd"] for log in self.usage_log if log["timestamp"] > one_day_ago)

    def get_cost_this_month(self) -> float:
        now = time.time()
        thirty_days_ago = now - (86400 * 30)
        return sum(log["cost_usd"] for log in self.usage_log if log["timestamp"] > thirty_days_ago)
    
    def get_stats(self) -> dict:
        if not self.usage_log:
            return {}
        
        model_usage = {}
        total_latency = 0
        fallbacks = 0
        
        for log in self.usage_log:
            model = log["model_used"]
            model_usage[model] = model_usage.get(model, 0) + 1
            total_latency += log["latency_ms"]
            if log["fallback_used"]:
                fallbacks += 1
                
        return {
            "most_used_model": max(model_usage, key=model_usage.get) if model_usage else None,
            "avg_latency": total_latency / len(self.usage_log),
            "fallback_rate": fallbacks / len(self.usage_log),
            "total_calls": len(self.usage_log)
        }

orchestrator = ModelOrchestrator()
