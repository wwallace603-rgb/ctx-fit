# windowfit

**Does your prompt actually fit in this model's context window?**

A zero-dependency CLI for planning token budgets against local LLM context limits. Know before you run whether your system prompt + user message + retrieved RAG context will overflow — and by how much.

> Built by [GhettoBoxAI](https://www.ghettoboxai.com/) — technical field reports on local LLMs, agents, RAG, and AI automation.

## Why this exists

You've got a 32K-context Qwen2.5 running locally. Your system prompt is 2K tokens. Your RAG pipeline retrieves 4 chunks × 1024 tokens each. You want 1K tokens of output. Does it fit?

Most token-cost tools assume you're paying per API call. Local models are free — but the window is hard. Overflow means truncated context, lost instructions, or a crash. `windowfit` answers this in one command, offline, no API key needed.

## Install

```bash
# npm (Node CLI)
npm install -g windowfit

# or one-shot:
npx windowfit --list

# PyPI (Python lib + CLI)
pip install windowfit
```

## Usage

### Quick fit check

```bash
# Does 8192 tokens of input fit in Llama 3.1 8B?
windowfit llama-3.1-8b 8192

# Same, but reserve 2048 tokens for output
windowfit llama-3.1-8b 8192 --reserve 2048
```

### RAG budget breakdown

```bash
# System: 2K, User: 512, Retrieved context: 4K, Reserve output: 1K
windowfit qwen2.5-7b --system 2048 --user 512 --context 4096 --reserve 1024
```

Output:
```
==================================================
  Qwen2.5 7B Instruct — Context Budget
==================================================

  Total window:          32K tokens
  ────────────────────────────────────────
  System prompt:        2K tokens  (6.2%)
  User message:       512 tokens  (1.6%)
  Retrieved ctx:        4K tokens  (12.5%)
  ────────────────────────────────────────
  Total input:          6.5K tokens  (20.3%)
  Output reserve:      1K tokens
  Usable budget:       31K tokens

  [PASS] Margin: +24.5K tokens
```

### List all known models

```bash
windowfit --list
```

### JSON output (for scripting)

```bash
windowfit llama-3.1-8b 4096 --json
# {"model":"llama-3.1-8b","context":131072,"input_tokens":4096,"fits":true,"margin":126976}
```

## Supported Models

| Family | Models | Context |
|--------|--------|---------|
| Llama 3.x | 1B, 3B, 8B, 70B | 128K |
| Mistral / Mixtral | 7B, 8x7B, 8x22B, Small 24B | 32K–128K |
| Qwen2.5 | 0.5B–32B, Coder 7B/32B | 32K |
| Gemma 2/3 | 9B, 27B, 4B, 12B | 8K–32K |
| Phi-3/3.5/4 | Mini, Medium, 14B | 4K–128K |
| DeepSeek R1 | Distill Qwen/Llama | 32K–128K |
| Cohere Command | R, R+ | 128K |

*Context windows reflect native model config. Some models support extended context via YaRN/position interpolation — check your serving framework.*

## When to use this

- **Before deploying a RAG pipeline** — verify your chunk count × chunk size + system prompt fits
- **When switching models** — "I'm moving from Llama 8B (128K) to Gemma 2 9B (8K). Does my prompt still fit?"
- **In CI/CD** — gate deployment on token budget: `windowfit $MODEL $TOKEN_COUNT --reserve $OUTPUT || exit 1`
- **When debugging truncation** — confirm whether your framework is silently dropping context

## Related Guides

- [LLM Ops Cheatsheet](https://www.ghettoboxai.com/llm-ops-cheatsheet/llm-ops-cheatsheet/) — practical local LLM operations
- [Building RAG Systems in Production](https://www.ghettoboxai.com/ai-agent-architecture/building-rag-systems-production/) — chunking, retrieval, context management
- [Prompt Engineering Playbook](https://www.ghettoboxai.com/prompt-engineering-playbook/prompt-engineering-playbook/) — 12 patterns that work

## License

[MIT](LICENSE)
