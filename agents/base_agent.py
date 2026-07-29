import ollama
import yaml
import json
import re
import os
import sys

from utils.token_tracker import log_usage
from data.rag.retriever import retrieve, build_context_block 
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "rag"))

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
ollama_client = ollama.Client(host=OLLAMA_HOST)


class BaseAgent:

    model_name: str = None
    system_prompt: str = ""
    temperature: float = None
    top_p: float = None
    top_k: int = None
    repeat_penalty: float = None
    max_tokens: int = None

    # --- RAG (desactive par defaut, chaque agent l'active explicitement) ---
    use_rag: bool = False
    rag_top_k: int = 4
    rag_type_filter: str = None  # ex: "pricing", "product", "faq", "objection", ou None = pas de filtre

    def __init__(self, config_path="config/llm.yaml"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        # If the subclass does not override a parameter,
        # use the default value from the configuration file.
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

    def get_rag_context(self, query: str, top_k: int = None, type_filter: str = None) -> str:
        """
        Interroge l'index FAISS (data/rag/index/) construit par rag/ingest.py
        et retourne un bloc de texte pret a etre injecte dans le prompt.
        Retourne "" si l'index n'existe pas encore ou si aucun resultat
        pertinent n'est trouve (l'agent continue de fonctionner normalement
        dans ce cas, juste sans contexte RAG).
        """
        
        try:
            results = retrieve(
                query,
                top_k=top_k if top_k is not None else self.rag_top_k,
                type_filter=type_filter if type_filter is not None else self.rag_type_filter,
            )
        except FileNotFoundError:
            # Index pas encore genere (python rag/ingest.py jamais lance) :
            # on ne bloque pas l'agent, on continue sans contexte.
            return ""
        return build_context_block(results)

    def call_llm(self, user_content: str, extra_messages: list = None, rag_query: str = None) -> str:
        system_content = self.system_prompt

        if self.use_rag:
            # rag_query permet a un agent de chercher sur un texte different
            # du message envoye au LLM (ex: chercher sur le sujet d'une reunion
            # mais poser une autre question au modele). Par defaut on cherche
            # sur user_content lui-meme.
            context = self.get_rag_context(rag_query or user_content)
            if context:
                system_content = f"{system_content}\n\n{context}"

        messages = [{"role": "system", "content": system_content}]

        if extra_messages: # Add conversation history when available.
            messages += extra_messages
        # Add the current user message.
        messages.append({"role": "user", "content": user_content})

        response = ollama_client.chat(
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

        prompt_tokens = response.get("prompt_eval_count", 0)
        response_tokens = response.get("eval_count", 0)
        log_usage(
            agent_name=self.__class__.__name__,
            prompt_tokens=prompt_tokens,
            response_tokens=response_tokens,
        )

        return (response["message"].get("content") or "").strip()
    def call_llm_raw(self, prompt: str, temperature: float = None, max_tokens: int = None) -> str:
        """Appel LLM SANS le system_prompt métier — pour des sous-tâches
        isolées (ex: classification) qui ne doivent pas être influencées
        par le contexte commercial."""
        response = ollama_client.chat(
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
        prompt_tokens = response.get("prompt_eval_count", 0)
        response_tokens = response.get("eval_count", 0)
        log_usage(
            agent_name=self.__class__.__name__,
            prompt_tokens=prompt_tokens,
            response_tokens=response_tokens,
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