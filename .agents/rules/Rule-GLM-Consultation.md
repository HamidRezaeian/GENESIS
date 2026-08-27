# Rule: GLM Oracle Consultation Protocol

When encountering complex architectural decisions, tensor-level mathematical formulations, edge-cases in physics rules (Rule 19, Rule 21), or before solidifying a new Substrate milestone, the agent MUST explicitly draft the consultation prompt for the user to send to GLM 5.3 (the external oracle).

### Behavior:
1. **Identify the Need**: Recognize when an architectural decision exceeds simple implementation and requires mathematical validation from GLM 5.3.
2. **Draft the Prompt**: Explicitly provide the exact text the user should copy and paste to GLM 5.3.
3. **Format**: Format the prompt clearly inside a markdown blockquote (`>`) or code block, written in Persian.
4. **Context**: Ensure the drafted prompt includes necessary context (e.g., current bottlenecks, specific Rule constraints, or the exact PyTorch tensor sizes) so GLM 5.3 can provide a highly specific, code-ready answer.

### Example Phrase:
"لطفاً این متن را کپی کرده و دقیقاً همین را از GLM 5.3 بپرسید:
> ما در حال پیاده‌سازی ... هستیم. لطفاً فرمول ریاضی دقیق برای ... را با در نظر گرفتن Rule 21 مشخص کن."
