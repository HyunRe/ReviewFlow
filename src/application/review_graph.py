from langgraph.graph import StateGraph, END
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from google.genai.errors import ServerError, APIError

from src.domain.models import ReviewState
from src.domain.diff_parser import DiffParser
from src.infrastructure.clients.llm_factory import LLMFactory
from src.infrastructure.cache.redis_client import RedisCacheManager
from src.infrastructure.persistence.database import ReviewRepository

# 분리한 LLM 지원 모듈 import
from src.infrastructure.clients.llm_calculator import (
    _get_available_claude_model,
    _get_available_gpt_model,
    _get_available_gemini_model,
    calculate_cost
)

redis_cache = RedisCacheManager()


# [추가] Gemini API 일시적 과부하(503, 429 등) 대비 재시도 데코레이터 함수
@retry(
    stop=stop_after_attempt(3),  # 최대 3회 재시도
    wait=wait_exponential(multiplier=1, min=2, max=10),  # 2초 -> 4초 -> 최대 10초 지연 대기
    retry=retry_if_exception_type((ServerError, APIError)),
    reraise=True
)
def call_gemini_with_retry(client, model_name, contents):
    """
    Gemini API 호출 시 서버 에러(503, 429 등) 발생 시 지수 백오프로 재시도하는 래퍼
    """
    return client.models.generate_content(model=model_name, contents=contents)


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
    selected_model = _get_available_claude_model(client)

    prompt = f"보안 관점에서 코드 리뷰를 진행해줘:\n{state['filtered_diff']}"
    res = client.messages.create(
        model=selected_model,
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )

    in_tokens = res.usage.input_tokens
    out_tokens = res.usage.output_tokens
    cost = calculate_cost(selected_model, in_tokens, out_tokens)

    return {
        "security_review": res.content[0].text,
        "total_tokens": state.get("total_tokens", 0) + in_tokens + out_tokens,
        "estimated_cost": state.get("estimated_cost", 0.0) + cost
    }


def performance_review_node(state: ReviewState) -> dict:
    client = LLMFactory.get_openai_client()
    selected_model = _get_available_gpt_model(client)

    prompt = f"성능 최적화 관점에서 코드 리뷰를 진행해줘:\n{state['filtered_diff']}"
    res = client.chat.completions.create(
        model=selected_model,
        messages=[{"role": "user", "content": prompt}]
    )

    in_tokens = res.usage.prompt_tokens
    out_tokens = res.usage.completion_tokens
    cost = calculate_cost(selected_model, in_tokens, out_tokens)

    return {
        "performance_review": res.choices[0].message.content,
        "total_tokens": state.get("total_tokens", 0) + in_tokens + out_tokens,
        "estimated_cost": state.get("estimated_cost", 0.0) + cost
    }


def style_review_node(state: ReviewState) -> dict:
    client = LLMFactory.get_gemini_client()
    selected_model = _get_available_gemini_model(client)

    prompt = f"코드 스타일 및 컨벤션 관점에서 코드 리뷰를 진행해줘:\n{state['filtered_diff']}"

    # [수정] 직접 generate_content를 호출하는 대신 재시도 래퍼 함수 적용
    try:
        res = call_gemini_with_retry(client, selected_model, prompt)
    except Exception as e:
        print(f"[WARNING] Gemini API failed after retries (503/429): {e}")
        raise e  # 필요에 따라 예외를 던지거나 Fallback 처리 가능

    in_tokens = res.usage_metadata.prompt_token_count if hasattr(res, 'usage_metadata') else 500
    out_tokens = res.usage_metadata.candidates_token_count if hasattr(res, 'usage_metadata') else 500
    cost = calculate_cost(selected_model, in_tokens, out_tokens)

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

    summary += f"---\n*📊 Total Tokens: {state.get('total_tokens', 0)} | Estimated Cost: ${state.get('estimated_cost', 0.0):.4f}*"

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