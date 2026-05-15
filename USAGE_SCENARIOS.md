# IP-XACT to LLD CLI Usage & Testing Scenarios

This document outlines the command line usages for testing the three core scenarios supported by the LLD Generator tool. 

> **Prerequisite:** Before running any command, ensure you are in the project root directory and have set your Python path:
> ```powershell
> # On Windows PowerShell
> $env:PYTHONPATH="src"
> 
> # On Linux/bash
> export PYTHONPATH="src"
> ```

---

## Scenario 1: First-Time Generation (No Existing LLD)

**Goal:** Generate a complete `lld.h` file from scratch when you are given the IP-XACT Excel sheet and `sfr.h` for the very first time. No git diffs or old code exist yet.

**Behavior:** The tool automatically filters out any registers containing "debug" in their description and generates `lld.h` from scratch based on the Excel semantics.

**Command:**
```powershell
python -m ipxact_lld_gen.cli `
  --excel sample/ipxact_sample.xlsx `
  --sfr-header sample/sfr_new.h `
  --out out_patch
```

**Verification:**
- Check `out_patch/lld.h` to see all generated LLD functions.
- `out_patch/run_report.json` will show `"mode": "first_time_generation"`.

---

## Scenario 2: Incremental Update (Patching Existing LLD)

**Goal:** Update an existing `lld.h` when a new version of the Excel file and a modified `sfr.h` are provided.

**Behavior:** The tool parses the `sfr.diff` to identify exactly which macros changed. It then uses an AST parser to surgically replace *only* the impacted functions in the existing `old_lld.h`, leaving any manual code untouched.

**Command:**
```powershell
python -m ipxact_lld_gen.cli `
  --excel sample/ipxact_sample.xlsx `
  --sfr-header sample/sfr_new.h `
  --existing-lld sample/old_lld.h `
  --sfr-diff sample/sfr.diff `
  --out out_patch
```

**Verification:**
- Check `out_patch/patched_lld.h` to see the updated file (your manual code remains untouched).
- Check `out_patch/patch_report.json` to see precisely which functions were replaced or inserted.

---

## Scenario 3: AI Model Generation (Using LLM)

**Goal:** Use a local AI model (e.g., Qwen via `llama.cpp`) to dynamically generate custom C function implementations based on the human-readable descriptions found in the Excel sheet.

**Behavior:** The tool intercepts the standard rule-engine. It sends the register description to the LLM endpoint specified in the config file. If the LLM successfully returns a C function, it uses it; otherwise, it falls back to the standard rule-engine automatically.

**Preparation:** Create a configuration file (e.g., `llm_config.json`) containing the API endpoint:
```json
{
  "api_url": "http://127.0.0.1:8080/v1/chat/completions",
  "model": "qwen",
  "timeout": 30
}
```

**Command (First-Time Generation + LLM):**
```powershell
python -m ipxact_lld_gen.cli `
  --excel sample/ipxact_sample.xlsx `
  --sfr-header sample/sfr_new.h `
  --out out_patch `
  --llm-config llm_config.json
```

**Command (Incremental Update + LLM):**
```powershell
python -m ipxact_lld_gen.cli `
  --excel sample/ipxact_sample.xlsx `
  --sfr-header sample/sfr_new.h `
  --existing-lld sample/old_lld.h `
  --sfr-diff sample/sfr.diff `
  --out out_patch `
  --llm-config llm_config.json
```

**Verification:**
- `patched_lld.h` or `lld.h` will contain the custom functions returned directly by the AI model.
- Check the console output; if the LLM server is down, it will log a timeout warning and fallback to the standard generation.

### Modifying the LLM API Integration

If you need to change how the AI model API is called (for example, to add Authentication tokens, change the JSON payload structure, or adjust the prompt), you need to modify the LLM client source code.

**File to Modify:** `src/ipxact_lld_gen/generator/llm_client.py`

**Key areas to update in the code:**
1. **The Prompt:** Look for the `prompt = f"""..."""` variable in `generate_lld_function()`. You can adjust the instructions given to the LLM to better format the generated C code.
2. **The JSON Payload:** Look for the `data = { ... }` dictionary. If your API requires different keys (like `max_tokens` instead of `temperature`, or specific nested structures), edit them here.
3. **Authentication Headers:** Look for the `headers={'Content-Type': 'application/json'}` line in the `urllib.request.Request` call. If your API (like OpenAI or a secure local server) requires a Bearer token, update it to:
   ```python
   headers={
       'Content-Type': 'application/json',
       'Authorization': 'Bearer YOUR_API_KEY' # Or load this from llm_config.json
   }
   ```
4. **Parsing the Response:** Look at `result["choices"][0]["message"]["content"]`. If you switch to an API that isn't strictly OpenAI-compatible, you will need to adjust the dictionary keys to correctly extract the generated text from the response.
