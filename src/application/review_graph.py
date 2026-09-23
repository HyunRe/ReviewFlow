from langgraph.graph import StateGraph, END
from src.domain.models import ReviewState
from src.domain.diff_parser import DiffParser
from src.infrastructure.clients.llm_factory import LLMFactory
from src.infrastructure.cache.redis_client import RedisCacheManager
from src.infrastructure.persistence.database import ReviewRepository

redis_cache = RedisCacheManager()

# 모델별 비용 단가 ($ / 1K Tokens) - 예시 단가
PRICE_PER_1K_TOKENS = {
    "claude-3-5-sonnet": {"input": 0.003, "output": 0.015},
    "gpt-4o": {"input": 0.0025, "output": 0.010},
    "gemini-3.5-flash": {"input": 0.000075, "output": 0.0003}
}


def _get_available_model(client) -> str:
    """현재 계정에서 지원하는 최신 Flash 모델을 탐색합니다."""
    try:
        models = list(client.models.list())
        priority_keywords = ['3.5-flash', '3.6-flash', '3.1-flash-lite', 'flash']

        for keyword in priority_keywords:
            for m in models:
                model_id = m.name.replace('models/', '')
                if keyword in model_id.lower():
                    print(f"[LLM] 동적 선택된 모델: {model_id}")
                    return model_id

        if models:
            selected = models[0].name.replace('models/', '')
            return selected
    except Exception as e:
        print(f"[LLM] 모델 목록 조회 실패, 기본값 사용: {e}")

    return 'gemini-3.5-flash'


def filter_diff_node(state: ReviewState) -> dict:
    compact_diff, files = DiffParser.parse(state.get("raw_diff", ""))
    return {"filtered_diff": compact_diff, "file_list": files}


def classify_diff_node(state: ReviewState) -> dict:
    diff = state.get("filtered_diff", "")
    if not diff:
        return {"has_security_risk": False, "has_performance_risk": False}
    return {"has_security_risk": True, "has_performance_risk": True}


def security_review_node(state: ReviewState) -> dict:
    client = LLMFactory.get_anthropic_client()
    prompt = f"보안 관점에서 코드 리뷰를 진행해줘:\n{state['filtered_diff']}"
    res = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )

    # 토큰 수 및 비용 계산
    in_tokens = res.usage.input_tokens
    out_tokens = res.usage.output_tokens
    cost = (in_tokens / 1000 * PRICE_PER_1K_TOKENS["claude-3-5-sonnet"]["input"]) + \
           (out_tokens / 1000 * PRICE_PER_1K_TOKENS["claude-3-5-sonnet"]["output"])

    return {
        "security_review": res.content[0].text,
        "total_tokens": state.get("total_tokens", 0) + in_tokens + out_tokens,
        "estimated_cost": state.get("estimated_cost", 0.0) + cost
    }


def performance_review_node(state: ReviewState) -> dict:
    client = LLMFactory.get_openai_client()
    prompt = f"성능 최적화 관점에서 코드 리뷰를 진행해줘:\n{state['filtered_diff']}"
    res = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )

    in_tokens = res.usage.prompt_tokens
    out_tokens = res.usage.completion_tokens
    cost = (in_tokens / 1000 * PRICE_PER_1K_TOKENS["gpt-4o"]["input"]) + \
           (out_tokens / 1000 * PRICE_PER_1K_TOKENS["gpt-4o"]["output"])

    return {
        "performance_review": res.choices[0].message.content,
        "total_tokens": state.get("total_tokens", 0) + in_tokens + out_tokens,
        "estimated_cost": state.get("estimated_cost", 0.0) + cost
    }


def style_review_node(state: ReviewState) -> dict:
    client = LLMFactory.get_gemini_client()

    # 동적 모델 선택 함수 호출
    selected_model = _get_available_model(client)

    prompt = f"코드 스타일 및 컨벤션 관점에서 코드 리뷰를 진행해줘:\n{state['filtered_diff']}"
    res = client.models.generate_content(
        model=selected_model,
        contents=prompt
    )

    in_tokens = res.usage_metadata.prompt_token_count if hasattr(res, 'usage_metadata') else 500
    out_tokens = res.usage_metadata.candidates_token_count if hasattr(res, 'usage_metadata') else 500

    # 동적으로 가져온 모델명이 Dict 키에 없을 경우 3.5-flash 단가를 기본값(fallback)으로 사용
    price_info = PRICE_PER_1K_TOKENS.get(selected_model, PRICE_PER_1K_TOKENS["gemini-3.5-flash"])
    cost = (in_tokens / 1000 * price_info["input"]) + (out_tokens / 1000 * price_info["output"])

    return {
        "style_review": res.text,
        "total_tokens": state.get("total_tokens", 0) + in_tokens + out_tokens,
        "estimated_cost": state.get("estimated_cost", 0.0) + cost
    }


def synthesize_node(state: ReviewState) -> dict:
    summary = "### 🤖 AI Code Review Summary\n\n"
    if state.get("security_review"): summary += f"#### 🔒 Security\n{state['security_review']}\n\n"
    if state.get("performance_review"): summary += f"#### ⚡ Performance\n{state['performance_review']}\n\n"
    if state.get("style_review"): summary += f"#### 🎨 Code Style\n{state['style_review']}\n\n"

    # 토큰/비용 소모 요약 추가
    summary += f"---\n*📊 Total Tokens: {state.get('total_tokens', 0)} | Estimated Cost: ${state.get('estimated_cost', 0.0):.4f}*"

    # Redis 캐시 저장 및 PostgreSQL DB 업데이트
    redis_cache.set_review_cache(state["commit_sha"], summary)
    ReviewRepository.update_status(
        history_id=state["review_history_id"],
        status="SUCCESS",
        total_tokens=state.get("total_tokens", 0),
        cost=state.get("estimated_cost", 0.0),
        summary=summary
    )

    return {"final_summary": summary}


def route_reviews(state: ReviewState):
    routes = ["style_review"]
    if state.get("has_security_risk"): routes.append("security_review")
    if state.get("has_performance_risk"): routes.append("performance_review")
    return routes


builder = StateGraph(ReviewState)
builder.add_node("filter_diff", filter_diff_node)
builder.add_node("classify_diff", classify_diff_node)
builder.add_node("security_review", security_review_node)
builder.add_node("performance_review", performance_review_node)
builder.add_node("style_review", style_review_node)
builder.add_node("synthesize", synthesize_node)

builder.set_entry_point("filter_diff")
builder.add_edge("filter_diff", "classify_diff")
builder.add_conditional_edges("classify_diff", route_reviews)
builder.add_edge("security_review", "synthesize")
builder.add_edge("performance_review", "synthesize")
builder.add_edge("style_review", "synthesize")
builder.add_edge("synthesize", END)

review_graph = builder.compile()