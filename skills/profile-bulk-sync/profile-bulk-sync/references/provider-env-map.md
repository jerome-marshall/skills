# Provider → ENV mapping for bulk sync

When user says "use anthropic / openai / google / minimax ..." map to:

| Provider keyword | ENV key in ~/.hermes/.env | config.yaml hint |
|---|---|---|
| openai, openai-api | OPENAI_API_KEY (+ optional OPENAI_BASE_URL) | model: { provider: openai-api, default: openai/gpt-4o } |
| anthropic, claude | ANTHROPIC_API_KEY | model: { default: anthropic/claude-sonnet-4 } |
| openrouter | OPENROUTER_API_KEY | model: { default: openrouter/xxx } |
| google, gemini | GOOGLE_API_KEY or GEMINI_API_KEY | model: { default: gemini/gemini-2.0-flash } |
| deepseek | DEEPSEEK_API_KEY | model: { default: deepseek/deepseek-chat } |
| xai, grok | XAI_API_KEY | model: { default: xai/grok-4 } |
| minimax, minimax-cn | MINIMAX_API_KEY / MINIMAX_CN_API_KEY | model: { default: minimax/minimax-m3 } |
| fireworks | FIREWORKS_API_KEY | model: { default: fireworks/xxx } |
| novita | NOVITA_API_KEY | model: { default: novita/xxx } |
| zai, glm | GLM_API_KEY | model: { default: zai/xxx } |
| kimi, moonshot | KIMI_API_KEY / KIMI_CN_API_KEY | model: { default: kimi-coding/xxx } |
| nous, portal | No key — OAuth via `hermes model` | model: { default: nous/xxx } |
| custom endpoint | CUSTOM_API_KEY + base_url | providers.<id>.base_url in config.yaml |

Multiple models = multiple env vars. Example: user wants to set primary to anthropic and fallback to openai -> set BOTH ANTHROPIC_API_KEY and OPENAI_API_KEY, plus model.default and model.fallback or fallback_providers.

Always use `hermes -p <name> config set KEY VAL` — it auto-routes secrets to .env.
