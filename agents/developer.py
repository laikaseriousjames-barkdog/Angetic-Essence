"""Knuth — Developer Agent. Full toolkit access for building, coding, creating."""

from core.base_agent import BaseAgent


class DeveloperAgent(BaseAgent):
    def __init__(self, config: dict, llm=None, kali=None):
        super().__init__("developer", config, llm, kali)

    def generate_code(self, prompt: str) -> str:
        self.logger.info(f"Code generation via LLM: {prompt[:100]}")
        return self.llm.generate_code(prompt)
