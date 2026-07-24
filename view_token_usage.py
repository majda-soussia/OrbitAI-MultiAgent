from utils.token_tracker import get_summary

if __name__ == "__main__":
    summary = get_summary()
    print(f"Total appels LLM : {summary['total_calls']}")
    print(f"Total tokens     : {summary['total_tokens']}")
    print("\nPar agent :")
    for agent, tokens in summary["by_agent"].items():
        print(f"  - {agent}: {tokens} tokens")