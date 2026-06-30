import ollama
import yaml
import json
import re
# Charger la config
with open("config/llm.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

with open("prompts/commercial.txt", "r", encoding="utf-8") as f:
    system_prompt = f.read()

with open("data/faq_objections.json", "r") as f:
    faq_data = json.load(f)

with open("data/sector_qualification.json", "r") as f:
    sector_data = json.load(f)

def clean_response(text: str) -> str:
    """
    Filet de sécurité : nettoie la réponse même si le modèle
    ignore les règles de formatage du prompt.
    """
    # Supprimer les headers markdown (##, ###, etc.)
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)

    # Supprimer les lignes de tableau markdown (| ... | ... |)
    text = re.sub(r'^\|.*\|$', '', text, flags=re.MULTILINE)

    # Supprimer les séparateurs de tableau (|---|---|)
    text = re.sub(r'^[\|\-\s:]+$', '', text, flags=re.MULTILINE)

    # Supprimer les lignes horizontales (---, ___, ***)
    text = re.sub(r'^[\-_\*]{3,}$', '', text, flags=re.MULTILINE)

    # Supprimer les emojis (plage Unicode large)
    emoji_pattern = re.compile(
        "["
        "\U0001F300-\U0001FAFF"
        "\U00002600-\U000027BF"
        "\U0001F1E0-\U0001F1FF"
        "]+",
        flags=re.UNICODE
    )
    text = emoji_pattern.sub('', text)

    # Supprimer le gras markdown excessif (**texte**) -> texte simple
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)

    # Supprimer les lignes vides multiples consécutives
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Supprimer les espaces en début/fin de ligne
    text = '\n'.join(line.strip() for line in text.split('\n'))

    return text.strip()


def commercial_agent(user_message: str, history: list = []):
    """Commercial Agent - Orbit AI Assistant"""

    messages = [{"role": "system", "content": system_prompt}]
    messages += history
    messages.append({"role": "user", "content": user_message})

    response = ollama.chat(
        model=config["model"]["name"],
        messages=messages,
        options={
            "temperature": config["parameters"]["temperature"],
            "top_p": config["parameters"]["top_p"],
            "top_k": config["parameters"]["top_k"],
            "repeat_penalty": config["parameters"]["repeat_penalty"],
            "num_predict": config["parameters"]["max_tokens"],
        }
    )

    raw_text = response["message"]["content"]
    cleaned_text = clean_response(raw_text)

    return cleaned_text


# TEST
if __name__ == "__main__":
    print("🤖 Orbit AI Assistant — Commercial Agent")
    print("=" * 50)

    history = []
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ["exit", "quit"]:
            break

        response = commercial_agent(user_input, history)
        print(f"\nOrbit AI: {response}")

        # Sauvegarder l'historique
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": response})