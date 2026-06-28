# Information Research

## Purpose

This document contains research and learning notes for the Layer 3 Classification & GuardRail layer of the XSignOn AI Native Security Testing project.

Layer 3 focuses on classifying prompts, enforcing safety boundaries, and deciding whether AI model interactions should be allowed, blocked, or flagged.

---

## 1. What Are AI Guardrails?

AI guardrails are safety and control layers around an AI system. They can check the user input before it reaches the model and check the model output before it is shown to the user.

Basic flow:

```text
User Prompt
→ Input Guardrail
→ LLM
→ Output Guardrail
→ Final Response
