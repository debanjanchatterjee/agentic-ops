from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, List

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langgraph.graph import END, StateGraph

from .config import SETTINGS
from .rag import load_vectorstore


ALLOWED_ACTIONS = {
    "restart_deployment",
    "scale_deployment",
    "clear_disk",
    "increase_memory_limit",
    "roll_back_config",
    "flush_dns_cache",
    "none",
}

ALLOWED_ROOT_CAUSES = {
    "pod_memory_oom",
    "service_unavailable",
    "disk_full",
    "dns_failure",
    "bad_config",
    "cpu_spike",
    "unknown",
}

ROOT_CAUSE_ACTION = {
    "pod_memory_oom": "increase_memory_limit",
    "service_unavailable": "restart_deployment",
    "disk_full": "clear_disk",
    "dns_failure": "flush_dns_cache",
    "bad_config": "roll_back_config",
    "cpu_spike": "scale_deployment",
    "unknown": "none",
}


@dataclass
class AgentState:
    alert: str
    logs: str
    context: str = ""
    diagnosis: str = ""
    action: str = ""
    runbook_update: str = ""


def _llm_disabled() -> bool:
    return os.getenv(SETTINGS.llm_disabled_env, "0") == "1"


def _get_llm() -> ChatOllama:
    return ChatOllama(model=SETTINGS.llm_model, base_url=SETTINGS.ollama_base_url, format="json")


def _safe_json_extract(text: str) -> Dict[str, str]:
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except Exception:
        return {}
    return {}


def _map_text_to_labels(text: str) -> Dict[str, str]:
    lower = text.lower()
    if "oom" in lower or "out of memory" in lower:
        return {"root_cause": "pod_memory_oom", "action": "increase_memory_limit"}
    if "disk" in lower and ("full" in lower or "pressure" in lower):
        return {"root_cause": "disk_full", "action": "clear_disk"}
    if "dns" in lower or "nxdomain" in lower:
        return {"root_cause": "dns_failure", "action": "flush_dns_cache"}
    if "config" in lower or "rollback" in lower:
        return {"root_cause": "bad_config", "action": "roll_back_config"}
    if "cpu" in lower and ("spike" in lower or "usage" in lower or "saturation" in lower):
        return {"root_cause": "cpu_spike", "action": "scale_deployment"}
    if "5xx" in lower or "unavailable" in lower or "connection refused" in lower or "timeout" in lower:
        return {"root_cause": "service_unavailable", "action": "restart_deployment"}
    return {}


def _normalize_root_cause(value: str, context: str) -> str:
    if value in ALLOWED_ROOT_CAUSES:
        return value
    mapped = _map_text_to_labels(f"{value}\n{context}")
    return mapped.get("root_cause", "unknown")


def _normalize_action(value: str, context: str) -> str:
    if value in ALLOWED_ACTIONS:
        return value
    mapped = _map_text_to_labels(context)
    return mapped.get("action", "none")


def _rule_based_diagnosis(alert: str, logs: str) -> Dict[str, str]:
    combined = f"{alert}\n{logs}".lower()
    if "oom" in combined or "out of memory" in combined:
        return {"root_cause": "pod_memory_oom", "action": "increase_memory_limit"}
    if "connection refused" in combined or "timeout" in combined:
        return {"root_cause": "service_unavailable", "action": "restart_deployment"}
    if "disk" in combined and "full" in combined:
        return {"root_cause": "disk_full", "action": "clear_disk"}
    if "cpu" in combined and ("spike" in combined or "usage" in combined or "saturation" in combined):
        return {"root_cause": "cpu_spike", "action": "scale_deployment"}
    if "dns" in combined or "nxdomain" in combined:
        return {"root_cause": "dns_failure", "action": "flush_dns_cache"}
    if "config" in combined and "rollback" in combined:
        return {"root_cause": "bad_config", "action": "roll_back_config"}
    return {"root_cause": "unknown", "action": "none"}


def retrieve_context(state: AgentState) -> AgentState:
    vectorstore = load_vectorstore()
    query = f"Alert: {state.alert}\nLogs: {state.logs}"
    docs = vectorstore.similarity_search(query, k=SETTINGS.top_k)
    context = "\n\n".join([doc.page_content for doc in docs])
    state.context = context
    return state


def diagnose(state: AgentState) -> AgentState:
    if _llm_disabled():
        result = _rule_based_diagnosis(state.alert, state.logs)
        state.diagnosis = result["root_cause"]
        state.action = result["action"]
        return state

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a DevOps incident triage agent. "
                "Return a compact JSON with keys root_cause and action. "
                f"Actions must be one of: {sorted(ALLOWED_ACTIONS)}.",
            ),
            (
                "human",
                "Alert:\n{alert}\n\nLogs:\n{logs}\n\nKB Context:\n{context}\n\n"
                "Return JSON only.",
            ),
        ]
    )

    llm = _get_llm()
    response = llm.invoke(prompt.format_messages(alert=state.alert, logs=state.logs, context=state.context))
    result = _safe_json_extract(response.content)
    if not result:
        combined = f"{response.content}\n{state.alert}\n{state.logs}"
        result = _map_text_to_labels(combined)
    if not result:
        result = _rule_based_diagnosis(state.alert, state.logs)
    combined = f"{state.alert}\n{state.logs}"
    state.diagnosis = _normalize_root_cause(result.get("root_cause", "unknown"), combined)
    # Force consistency between root cause and action for reproducible metrics.
    # Action is derived from the normalized root cause.
    state.action = ROOT_CAUSE_ACTION.get(state.diagnosis, "none")
    return state


def safety_check(state: AgentState) -> AgentState:
    if state.action not in ALLOWED_ACTIONS:
        state.action = "none"
    return state


def scribe(state: AgentState) -> AgentState:
    summary = (
        f"Incident triage summary:\n"
        f"- Root cause: {state.diagnosis}\n"
        f"- Recommended action: {state.action}\n"
    )
    state.runbook_update = summary
    return state


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("retrieve", RunnableLambda(retrieve_context))
    graph.add_node("diagnose", RunnableLambda(diagnose))
    graph.add_node("safety", RunnableLambda(safety_check))
    graph.add_node("scribe", RunnableLambda(scribe))

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "diagnose")
    graph.add_edge("diagnose", "safety")
    graph.add_edge("safety", "scribe")
    graph.add_edge("scribe", END)
    return graph.compile()


def run_incident(alert: str, logs: str) -> AgentState:
    app = build_graph()
    result = app.invoke(AgentState(alert=alert, logs=logs))
    if isinstance(result, AgentState):
        return result
    return AgentState(**result)


def allowed_actions() -> List[str]:
    return sorted(ALLOWED_ACTIONS)
