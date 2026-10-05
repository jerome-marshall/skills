# June 2026 Parameter Passing Bug (cronjob create)

## Symptoms
- `cronjob(action='create', schedule='0 7 * * *', prompt='...')` repeatedly returned:
  - "schedule is required for create"
  - "create requires either prompt or at least one skill"
- `cronjob(action='list')` worked fine.

## Investigation Path
1. Confirmed list works → tool is registered.
2. Read `~/.hermes/hermes-agent/tools/cronjob_tools.py` (the implementation of the `cronjob` tool function).
3. Found the exact check at lines 488-490:
   ```python
   if normalized == "create":
       if not schedule:
           return tool_error("schedule is required for create", success=False)
   ```
4. Conclusion: parameters were being dropped by the function-calling / XML parser layer before reaching Python.

## Context
- Model: grok-4.3 (xAI)
- Tool: cronjob (complex tool with ~20 parameters)
- Date: June 2026

This appears to be a schema / serialization edge case with large optional-parameter tools rather than a user mistake.