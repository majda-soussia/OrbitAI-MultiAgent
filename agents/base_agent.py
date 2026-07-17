import ollama
import yaml
import json
import re


class BaseAgent:

    model_name: str = None
    system_prompt: str = ""
    temperature: float = None
    top_p: float = None
    top_k: int = None
    repeat_penalty: float = None
    max_tokens: int = None

    def __init__(self, config_path="config/llm.yaml"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        # Si la sous-classe n'override pas une valeur, on prend le défaut du yaml
        if self.model_name is None:
            self.model_name = self.config["model"]["name"]
        if self.temperature is None:
            self.temperature = self.config["parameters"].get("temperature", 0.3)
        if self.top_p is None:
            self.top_p = self.config["parameters"].get("top_p", 0.8)
        if self.top_k is None:
            self.top_k = self.config["parameters"].get("top_k", 40)
        if self.repeat_penalty is None:
            self.repeat_penalty = self.config["parameters"].get("repeat_penalty", 1.1)
        if self.max_tokens is None:
            self.max_tokens = self.config["parameters"].get("max_tokens", 1000)

    def call_llm(self, user_content: str, extra_messages: list = None) -> str:
        messages = [{"role": "system", "content": self.system_prompt}]

        if extra_messages: # Add conversation history when available.
            messages += extra_messages
        # Add the current user message.
        messages.append({"role": "user", "content": user_content})

        response = ollama.chat(
            model=self.model_name,
            messages=messages,
            options={
                "temperature": self.temperature,
                "top_p": self.top_p,
                "top_k": self.top_k,
                "repeat_penalty": self.repeat_penalty,
                "num_predict": self.max_tokens,
            }
        )

        return (response["message"].get("content") or "").strip()
    def call_llm_raw(self, prompt: str, temperature: float = None, max_tokens: int = None) -> str:
        """Appel LLM SANS le system_prompt métier — pour des sous-tâches
        isolées (ex: classification) qui ne doivent pas être influencées
        par le contexte commercial."""
        response = ollama.chat(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            options={
                "temperature": temperature if temperature is not None else self.temperature,
                "top_p": self.top_p,
                "top_k": self.top_k,
                "repeat_penalty": self.repeat_penalty,
                "num_predict": max_tokens if max_tokens is not None else self.max_tokens,
            }
        )
        return (response["message"].get("content") or "").strip()
    @staticmethod
    def extract_json_from_text(text: str) -> str:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end < start:
            return ""
        return text[start:end + 1]

    def parse_json_response(self, raw_text: str, fallback: dict) -> dict:
        if "<think>" in raw_text and "</think>" in raw_text:
            raw_text = raw_text.split("</think>")[-1].strip()

        if raw_text.startswith("```"):
            raw_text = (
                raw_text.strip("`")
                .replace("json\n", "")
                .replace("json", "", 1)
            )

        json_candidate = self.extract_json_from_text(raw_text)

        try:
            return json.loads(json_candidate if json_candidate else raw_text)
        except json.JSONDecodeError:
            fallback["_raw_model_output"] = raw_text
            return fallback

    @staticmethod
    def clean_text_response(text: str) -> str:
        """
        Filet de sécurité pour les agents conversationnels (texte libre) :
        supprime markdown, emojis, séparateurs indésirables.
        Utile pour Commercial Agent, Reply Agent... pas pour les agents JSON.
        """
        text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\|.*\|$', '', text, flags=re.MULTILINE)
        text = re.sub(r'^[\|\-\s:]+$', '', text, flags=re.MULTILINE)
        text = re.sub(r'^[\-_\*]{3,}$', '', text, flags=re.MULTILINE)

        emoji_pattern = re.compile(
            "["
            "\U0001F300-\U0001FAFF"
            "\U00002600-\U000027BF"
            "\U0001F1E0-\U0001F1FF"
            "]+",
            flags=re.UNICODE
        )
        text = emoji_pattern.sub('', text)

        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = '\n'.join(line.strip() for line in text.split('\n'))

        return text.strip()

    def run(self, *args, **kwargs):
        raise NotImplementedError("Each agent must implement the run() method.")