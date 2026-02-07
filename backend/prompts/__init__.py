"""Prompt templates for LLM reasoner."""

from backend.prompts.system_prompt import (
    SYSTEM_PROMPT,
    GUIDANCE_PROMPT_TEMPLATE,
    ISSUE_PROMPTS,
    LANGUAGE_TEMPLATES,
    ENCOURAGEMENT_MESSAGES,
    FALLBACK_GUIDANCE,
    get_issue_prompt,
    get_language_template,
    get_encouragement,
    format_guidance_prompt
)

__all__ = [
    "SYSTEM_PROMPT",
    "GUIDANCE_PROMPT_TEMPLATE",
    "ISSUE_PROMPTS",
    "LANGUAGE_TEMPLATES",
    "ENCOURAGEMENT_MESSAGES",
    "FALLBACK_GUIDANCE",
    "get_issue_prompt",
    "get_language_template",
    "get_encouragement",
    "format_guidance_prompt"
]
