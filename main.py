from agents.orchestrator_agent import OrchestratorAgent


def print_banner():
    print("=" * 50)
    print("  ORBIT AI ASSISTANT")
    print("  Commercial · Email · Planning")
    print("=" * 50)
    print("Tapez votre message. 'exit' ou 'quit' pour sortir.\n")


def format_response(result: dict) -> str:
    agent = result["agent"]
    response = result["response"]

    if agent == "email":
        # response est une liste de dicts JSON (analyses d'emails)
        lines = [f"[{len(response)} email(s) analysé(s)]"]
        for r in response:
            lines.append(
                f"  - ({r.get('priority', '?')}) {r.get('subject', '(no subject)')} "
                f"— {r.get('summary', '')}"
            )
        return "\n".join(lines)

    # planning et commercial retournent déjà du texte prêt à afficher
    return str(response)


def main():
    print_banner()
    orchestrator = OrchestratorAgent()

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAu revoir.")
            break

        if not user_input:
            continue

        if user_input.lower() in ["exit", "quit"]:
            print("Au revoir.")
            break

        result = orchestrator.run(user_input)
        print(f"\n[{result['agent'].upper()}]")
        print(format_response(result))
        print()


if __name__ == "__main__":
    main()