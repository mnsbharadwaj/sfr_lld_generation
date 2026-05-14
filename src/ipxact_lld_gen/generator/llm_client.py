from __future__ import annotations
import urllib.request
import urllib.error
import json
import logging

log = logging.getLogger(__name__)

class LlmClient:
    def __init__(self, config_path: str):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        self.api_url = self.config.get("api_url", "http://127.0.0.1:8080/v1/chat/completions")
        self.model = self.config.get("model", "qwen")
        self.timeout = self.config.get("timeout", 30)

    def generate_lld_function(self, description: str, field_key: str, reg: str, field: str, access: str) -> str | None:
        if not description.strip():
            return None

        prompt = f"""
You are an expert C embedded systems programmer.
Generate a single `static inline` C function based on the following description.
Only output the raw C code, no markdown formatting, no explanation.
Ensure the function name relates to: {field_key}

Field Key: {field_key}
Register: {reg}
Field: {field}
Access Type: {access}

Description:
{description}
"""
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a helpful coding assistant. Output only raw code."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1
        }
        
        req = urllib.request.Request(
            self.api_url, 
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                result = json.loads(response.read().decode('utf-8'))
                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"]["content"]
                    # Strip markdown block if model ignored the system prompt
                    if content.startswith("```"):
                        lines = content.splitlines()
                        if lines[0].startswith("```"):
                            lines = lines[1:]
                        if lines and lines[-1].startswith("```"):
                            lines = lines[:-1]
                        return "\n".join(lines).strip()
                    return content.strip()
        except Exception as e:
            log.warning(f"LLM generation failed for {field_key}: {e}")
            return None
        return None
