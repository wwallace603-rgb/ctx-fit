import argparse
import json
import os
import sys

def load_models():
    path = os.path.join(os.path.dirname(__file__), "models.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)["models"]

def find_model(models, query):
    q = query.lower().strip()
    # Exact id match
    for m in models:
        if m["id"] == q:
            return m
    # Partial id match
    matches = [m for m in models if q in m["id"]]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        ids = ", ".join(m["id"] for m in matches[:5])
        print(f"Multiple matches: {ids}", file=sys.stderr)
        sys.exit(1)
    # Name match
    for m in models:
        if q in m["name"].lower():
            return m
    return None

def fmt_tokens(n):
    if n >= 1024:
        return f"{n/1024:.1f}K" if n % 1024 != 0 else f"{n//1024}K"
    return str(n)

def show_model(model, verbose=False):
    print(f"\n  {model['name']}")
    print(f"  ID:         {model['id']}")
    print(f"  Parameters: {model['params_b']}B")
    print(f"  Context:    {fmt_tokens(model['context'])} tokens ({model['context']:,})")
    if verbose:
        print(f"\n  Quick check: llm-fit {model['id']} <your_token_count>")
        print(f"  Budget:      llm-fit {model['id']} --system 2048 --user 1024 --context 4096 --reserve 512")

def fit_check(model, total_input, reserve=0):
    ctx = model["context"]
    usable = ctx - reserve
    fits = total_input <= usable
    pct = (total_input / ctx) * 100 if ctx > 0 else 0
    margin = usable - total_input

    status = "PASS" if fits else "FAIL"
    print(f"\n  Model:      {model['name']} ({fmt_tokens(ctx)} context)")
    print(f"  Input:      {fmt_tokens(total_input)} tokens")
    if reserve:
        print(f"  Reserve:    {fmt_tokens(reserve)} tokens (for output)")
    print(f"  Usable:     {fmt_tokens(usable)} tokens")
    print(f"  Usage:      {pct:.1f}% of context window")
    print(f"  Margin:     {'+' if margin >= 0 else ''}{fmt_tokens(abs(margin))} tokens")
    print(f"\n  Result:     [{status}] {'FITS' if fits else 'DOES NOT FIT'}")

    if not fits:
        overflow = total_input - usable
        print(f"  Overflow:   {fmt_tokens(overflow)} tokens over budget")
        # Suggest smaller models or less context
        small_enough = [m for m in load_models() if (m["context"] - reserve) >= total_input]
        if small_enough:
            names = ", ".join(m["id"] for m in sorted(small_enough, key=lambda x: x["context"])[:3])
            print(f"  Tip:        Try a model with larger window: {names}")
    return fits

def budget_breakdown(model, system=0, user=0, context=0, reserve=0):
    ctx = model["context"]
    total_input = system + user + context
    usable = ctx - reserve

    print(f"\n  {'='*50}")
    print(f"  {model['name']} — Context Budget")
    print(f"  {'='*50}\n")
    print(f"  Total window:     {fmt_tokens(ctx):>10} tokens")
    print(f"  {'─'*40}")
    if system:
        pct_s = (system/ctx)*100
        print(f"  System prompt:    {fmt_tokens(system):>10} tokens  ({pct_s:.1f}%)")
    if user:
        pct_u = (user/ctx)*100
        print(f"  User message:     {fmt_tokens(user):>10} tokens  ({pct_u:.1f}%)")
    if context:
        pct_c = (context/ctx)*100
        print(f"  Retrieved ctx:    {fmt_tokens(context):>10} tokens  ({pct_c:.1f}%)")
    print(f"  {'─'*40}")
    print(f"  Total input:      {fmt_tokens(total_input):>10} tokens  ({(total_input/ctx)*100:.1f}%)")
    if reserve:
        print(f"  Output reserve:   {fmt_tokens(reserve):>10} tokens")
    print(f"  Usable budget:    {fmt_tokens(usable):>10} tokens")
    margin = usable - total_input
    status = "PASS" if margin >= 0 else "FAIL"
    print(f"\n  [{'PASS' if margin>=0 else 'FAIL'}] Margin: {'+' if margin>=0 else ''}{fmt_tokens(abs(margin))} tokens")

    if margin < 0:
        # How many chunks of context can fit?
        if context > 0:
            avg_chunk = context / max(1, 1)  # just show what fits
            remaining = usable - system - user
            if remaining > 0:
                print(f"  Tip: You can fit ~{fmt_tokens(remaining)} tokens of retrieved context")

def list_models(models):
    print(f"\n  Known Local LLMs ({len(models)} models)\n")
    # Group by context size
    groups = {}
    for m in sorted(models, key=lambda x: (-x["context"], x["params_b"])):
        ctx_key = m["context"]
        if ctx_key not in groups:
            groups[ctx_key] = []
        groups[ctx_key].append(m)

    for ctx in sorted(groups.keys(), reverse=True):
        label = fmt_tokens(ctx)
        print(f"  {label} context:")
        for m in groups[ctx]:
            print(f"    {m['id']:<35} {m['params_b']:>5}B")
        print()

def main():
    parser = argparse.ArgumentParser(
        prog="llm-fit",
        description="Check if your prompt fits in a local LLM's context window. Zero dependencies, works offline.",
        epilog="Model data at: https://github.com/wwallace603-rgb/llm-fit"
    )
    parser.add_argument("model", nargs="?", help="Model ID (e.g., llama-3.1-8b, qwen2.5-7b)")
    parser.add_argument("tokens", nargs="?", type=int, help="Total input tokens to check")
    parser.add_argument("--system", "-s", type=int, default=0, help="System prompt tokens")
    parser.add_argument("--user", "-u", type=int, default=0, help="User message tokens")
    parser.add_argument("--context", "-c", type=int, default=0, help="Retrieved context tokens (RAG)")
    parser.add_argument("--reserve", "-r", type=int, default=0, help="Tokens reserved for output generation")
    parser.add_argument("--list", "-l", action="store_true", help="List all known models")
    parser.add_argument("--json", "-j", action="store_true", help="JSON output")
    args = parser.parse_args()

    models = load_models()

    if args.list or not args.model:
        list_models(models)
        return

    model = find_model(models, args.model)
    if not model:
        print(f"Unknown model '{args.model}'. Use --list to see available models.", file=sys.stderr)
        sys.exit(1)

    # Budget mode (any of --system/--user/--context specified)
    if args.system or args.user or args.context:
        budget_breakdown(model, args.system, args.user, args.context, args.reserve)
        return

    # Quick fit check
    if args.tokens:
        result = fit_check(model, args.tokens, args.reserve)
        if args.json:
            print(json.dumps({
                "model": model["id"],
                "context": model["context"],
                "input_tokens": args.tokens,
                "reserve": args.reserve,
                "fits": result,
                "margin": model["context"] - args.reserve - args.tokens
            }))
        return

    # Just show model info
    if args.json:
        print(json.dumps(model, indent=2))
    else:
        show_model(model, verbose=True)

if __name__ == "__main__":
    main()
