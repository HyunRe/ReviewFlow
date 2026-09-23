# 모델별 비용 단가 ($ / 1K Tokens)
PRICE_PER_1K_TOKENS = {
    # Anthropic Claude
    "claude-4-6-sonnet": {"input": 0.003, "output": 0.015},
    "claude-5-sonnet": {"input": 0.003, "output": 0.015},
    "claude-4-5-haiku": {"input": 0.0008, "output": 0.004},
    "claude-5-5-opus": {"input": 0.015, "output": 0.075},
    "claude-5-fable": {"input": 0.003, "output": 0.015},
    "claude-5-1-fable": {"input": 0.003, "output": 0.015},
    "claude-3-5-sonnet-latest": {"input": 0.003, "output": 0.015},

    # OpenAI GPT
    "gpt-5-6-luna": {"input": 0.0025, "output": 0.010},
    "gpt-4o": {"input": 0.0025, "output": 0.010},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},

    # Google Gemini
    "gemini-3.5-flash": {"input": 0.000075, "output": 0.0003},
    "gemini-3.6-flash": {"input": 0.000075, "output": 0.0003},
}


def _get_available_claude_model(client) -> str:
    """Anthropic API: 최신 Claude 모델 동적 탐색"""
    try:
        response = client.models.list()
        models = response.data
        priority_keywords = [
            'claude-4-6-sonnet',
            'claude-5-sonnet',
            'claude-4-5-haiku',
            'claude-5-5-opus',
            'claude-5-1-fable',
            'claude-5-fable',
            'sonnet',
            'haiku'
        ]

        for keyword in priority_keywords:
            for m in models:
                if keyword in m.id.lower():
                    print(f"[LLM-Claude] 동적 선택된 모델: {m.id}")
                    return m.id

        if models:
            return models[0].id
    except Exception as e:
        print(f"[LLM-Claude] 모델 목록 조회 실패, 기본값 사용: {e}")

    return 'claude-4-6-sonnet'


def _get_available_gpt_model(client) -> str:
    """OpenAI API: GPT-5.6 Luna 및 GPT-4o 동적 탐색"""
    try:
        models = list(client.models.list())
        priority_keywords = ['gpt-5.6-luna', 'gpt-5-6-luna', 'gpt-4o', 'gpt-4o-mini']

        for keyword in priority_keywords:
            for m in models:
                if keyword in m.id.lower():
                    print(f"[LLM-GPT] 동적 선택된 모델: {m.id}")
                    return m.id

        if models:
            return models[0].id
    except Exception as e:
        print(f"[LLM-GPT] 모델 목록 조회 실패, 기본값 사용: {e}")

    return 'gpt-5-6-luna'


def _get_available_gemini_model(client) -> str:
    """Gemini API: 사용 가능한 최신 Flash 모델 탐색"""
    try:
        models = list(client.models.list())
        priority_keywords = ['3.5-flash', '3.6-flash', 'flash']

        for keyword in priority_keywords:
            for m in models:
                model_id = m.name.replace('models/', '')
                if keyword in model_id.lower():
                    print(f"[LLM-Gemini] 동적 선택된 모델: {model_id}")
                    return model_id

        if models:
            return models[0].name.replace('models/', '')
    except Exception as e:
        print(f"[LLM-Gemini] 모델 목록 조회 실패, 기본값 사용: {e}")

    return 'gemini-3.5-flash'


def calculate_cost(model_name: str, input_tokens: int, output_tokens: int) -> float:
    """단가 표 조회를 안전하게 처리하는 토큰 비용 계산 함수"""
    default_price = {"input": 0.000075, "output": 0.0003}
    price_info = PRICE_PER_1K_TOKENS.get(model_name, default_price)

    input_cost = (input_tokens / 1000) * price_info["input"]
    output_cost = (output_tokens / 1000) * price_info["output"]

    return round(input_cost + output_cost, 6)