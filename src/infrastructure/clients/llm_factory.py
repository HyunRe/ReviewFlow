import os
from google import genai
from anthropic import Anthropic
from openai import OpenAI

class LLMFactory:
    @staticmethod
    def get_gemini_client():
        return genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    @staticmethod
    def get_anthropic_client():
        return Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    @staticmethod
    def get_openai_client():
        return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))