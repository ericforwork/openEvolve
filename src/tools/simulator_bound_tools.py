"""
CrewAI tools whose names／介面對齊 tasks_simulator.yaml（search_*、lookup_*、search_internet），
底層改走 Simulator 注入的 InteractionTool（與競賽資料一致）。
未安裝 Serper 時 search_internet 為 stub，避免缺依賴。
"""
from __future__ import annotations

import os
import re

from crewai.tools import tool

from src.tools import interaction_tool_wrapper as _itw


def _interaction():
    return _itw.get_injected_interaction_tool()


_ID_TOKEN = r"[\w\-]+"


def _extract_user_id(search_query: str) -> str | None:
    for pattern in (
        rf"user_id\s*(?:is|:)\s*({_ID_TOKEN})",
        rf"for user\s+({_ID_TOKEN})",
        rf"user\s+({_ID_TOKEN})",
    ):
        m = re.search(pattern, search_query, re.I)
        if m:
            return m.group(1)
    return None


def _extract_item_id(search_query: str) -> str | None:
    for pattern in (
        rf"item_id\s*(?:is|:)\s*({_ID_TOKEN})",
        rf"for business\s+({_ID_TOKEN})",
        rf"business\s+({_ID_TOKEN})",
        rf"item\s+({_ID_TOKEN})",
    ):
        m = re.search(pattern, search_query, re.I)
        if m:
            return m.group(1)
    return None


@tool("search_user_profile_data")
def search_user_profile_data(search_query: str) -> str:
    """以自然語言 search_query 查詢使用者 profile（須含 user_id）。"""
    it = _interaction()
    if it is None:
        return "Error: InteractionTool has not been injected by the Simulator."
    user_id = _extract_user_id(search_query)
    if not user_id:
        return (
            "Error: include user_id in search_query, e.g. "
            "'What are the review habits for user <user_id>'"
        )
    u = it.get_user(user_id=user_id)
    return str(u) if u is not None else "No user found"


@tool("search_restaurant_feature_data")
def search_restaurant_feature_data(search_query: str) -> str:
    """以自然語言 search_query 查詢商家／商品 profile（須含 item_id）。"""
    it = _interaction()
    if it is None:
        return "Error: InteractionTool has not been injected by the Simulator."
    item_id = _extract_item_id(search_query)
    if not item_id:
        return (
            "Error: include item_id in search_query, e.g. "
            "'What are the categories for business <item_id>'"
        )
    item = it.get_item(item_id=item_id)
    return str(item) if item is not None else "No item found"


@tool("search_historical_reviews_data")
def search_historical_reviews_data(search_query: str) -> str:
    """以自然語言 search_query 查詢歷史評論（search_query 須含 user_id 或 item_id）。"""
    it = _interaction()
    if it is None:
        return "Error: InteractionTool has not been injected by the Simulator."
    user_id = _extract_user_id(search_query)
    item_id = _extract_item_id(search_query)
    if user_id and item_id:
        reviews = it.get_reviews(item_id=item_id) or []
        matched = [r for r in reviews if str(r.get("user_id", "")) == str(user_id)]
        if matched:
            return str(matched)
        ur = it.get_reviews(user_id=user_id) or []
        return str(ur) if ur else "No reviews found for this user-item pair."
    if user_id:
        reviews = it.get_reviews(user_id=user_id) or []
        return str(reviews) if reviews else "No reviews found for this user."
    if item_id:
        reviews = it.get_reviews(item_id=item_id) or []
        return str(reviews) if reviews else "No reviews found for this item."
    return (
        "Error: include user_id or item_id in search_query, e.g. "
        "'past reviews where user_id is <id>' or 'reviews about business <item_id>'"
    )


@tool("lookup_user_by_id")
def lookup_user_by_id(user_id: str) -> str:
    """依 user_id 取得使用者 profile（來自 Simulator 的 InteractionTool）。"""
    it = _interaction()
    if it is None:
        return "Error: InteractionTool has not been injected by the Simulator."
    u = it.get_user(user_id=user_id)
    return str(u) if u is not None else "No user found"


@tool("lookup_item_by_id")
def lookup_item_by_id(item_id: str) -> str:
    """依 item_id 取得商家／商品 profile。"""
    it = _interaction()
    if it is None:
        return "Error: InteractionTool has not been injected by the Simulator."
    item = it.get_item(item_id=item_id)
    return str(item) if item is not None else "No item found"


@tool("lookup_reviews_by_user_and_item")
def lookup_reviews_by_user_and_item(user_id: str, item_id: str) -> str:
    """取得與 user、item 相關的評論（先取 item 下評論再篩 user）。"""
    it = _interaction()
    if it is None:
        return "Error: InteractionTool has not been injected by the Simulator."
    reviews = it.get_reviews(item_id=item_id) or []
    matched = [r for r in reviews if str(r.get("user_id", "")) == str(user_id)]
    if matched:
        return str(matched)
    # fallback：使用者所有評論
    ur = it.get_reviews(user_id=user_id) or []
    return str(ur) if ur else "No reviews found for this user-item pair."


@tool("lookup_reviews_by_item")
def lookup_reviews_by_item(item_id: str) -> str:
    """依 item_id 取得該商家相關評論列表。"""
    it = _interaction()
    if it is None:
        return "Error: InteractionTool has not been injected by the Simulator."
    reviews = it.get_reviews(item_id=item_id) or []
    return str(reviews) if reviews else "No reviews found for this item."


@tool("lookup_reviews_by_user")
def lookup_reviews_by_user(user_id: str) -> str:
    """依 user_id 取得該使用者相關評論列表。"""
    it = _interaction()
    if it is None:
        return "Error: InteractionTool has not been injected by the Simulator."
    reviews = it.get_reviews(user_id=user_id) or []
    return str(reviews) if reviews else "No reviews found for this user."


def _stub_search_internet():
    @tool("search_internet")
    def search_internet(search_query: str) -> str:
        """未設定 SERPER_API_KEY 時的網搜占位：回傳一般性評分行為說明。"""
        return (
            "Internet search is not configured (install crewai-tools + SERPER_API_KEY for live search). "
            "Use general patterns only: 1–2 stars often reflect service/quality issues; 4–5 stars reflect satisfaction; "
            "factors include food, service, price, wait time, atmosphere. Query was: "
            + str(search_query)[:200]
        )

    return search_internet


def get_search_internet_tool():
    """有 SERPER_API_KEY 時使用 SerperDevTool；否則回傳 stub。"""
    if os.getenv("SERPER_API_KEY") or os.getenv("SERPAPI_API_KEY"):
        try:
            from crewai_tools import SerperDevTool

            return SerperDevTool(
                name="search_internet",
                description=(
                    "Search the internet for general restaurant review trends and rating behavior. "
                    "Input key must be search_query."
                ),
            )
        except Exception:
            pass
    return _stub_search_internet()


@tool("delegate_work_to_coworker")
def delegate_work_to_coworker(
    coworker: str = "",
    task: str = "",
    context: str = "",
) -> str:
    """
    專案經理委派用（與 agents 設定一致）。Sequential crew 已會依序執行各 task，
    此工具僅作為讓 LLM 以正確格式完成委派敘述的掛鉤。
    """
    return (
        f"Delegation recorded (sequential pipeline continues automatically). "
        f"coworker={coworker!r}, task={task!r}, context={context[:300]!r}"
    )
