# Spark Integration Guide

Easily integrate Spark's micro-app generation capabilities into any LLM agent or chat interface.

## Quick Links
- [OpenAI ChatGPT Actions](#openai-chatgpt-actions)
- [LangChain](#langchain-python)
- [Vercel AI SDK](#vercel-ai-sdk)
- [Raw API / Curl](#raw-api)
- [Magic Links](#magic-links)

---

## OpenAI ChatGPT Actions

Use Spark as a custom action in your GPT.

1. Go to **My GPTs** > **Create a GPT** > **Configure** > **Create new action**.
2. **Schema**: Import from URL `https://your-spark-domain.com/static/openai-actions.yaml` (or copy contents from `backend/static/openai-actions.yaml`).
3. **Authentication**: Set to `None` (or API Key if you configured auth).

---

## LangChain (Python)

Copy this tool definition to give your LangChain agent the ability to generate UIs.

```python
from langchain.tools import tool
import requests

SPARK_API_URL = "http://localhost:8000" # Replace with your deployment URL

@tool
def generate_ui(prompt: str, data: dict = None):
    """
    Generates an interactive UI/Chart/Dashboard micro-app.
    Use this when the user asks to "visualize", "show", "chart", or "plot" data.
    
    Args:
        prompt: Description of the UI (e.g. "Bar chart of sales by region")
        data: Optional dictionary of data to visualize.
    """
    response = requests.post(
        f"{SPARK_API_URL}/api/a2a/generate",
        json={"prompt": prompt, "data_context": data}
    )
    result = response.json()
    
    if result["status"] == "success":
        return f"UI Generated successfully: {result['microapp_url']}"
    elif result["status"] == "needs_info":
        return f"I need more data to generate this. Missing schema: {result['missing_info']}"
    else:
        return f"Generation failed: {result['message']}"
```

---

## Vercel AI SDK

For use with `useChat` or `generateText`.

```typescript
import { z } from 'zod';

const tools = {
  generate_ui: {
    description: 'Generates a UI component or chart',
    parameters: z.object({
      prompt: z.string().describe('Description of the UI to build'),
      data: z.record(z.any()).optional().describe('Data to visualize'),
    }),
    execute: async ({ prompt, data }) => {
      const response = await fetch('https://your-spark-domain.com/api/a2a/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, data_context: data }),
      });
      const result = await response.json();
      return result;
    },
  },
};
```

---

## Raw API

### Endpoint: `POST /api/a2a/generate`

**Request:**
```json
{
  "prompt": "Create a sales dashboard for Q4",
  "data_context": {
    "sales": [
      {"month": "Oct", "value": 100},
      {"month": "Nov", "value": 150},
      {"month": "Dec", "value": 200}
    ]
  }
}
```

**Response:**
```json
{
  "status": "success",
  "microapp_url": "https://spark.domain/api/components/123/iframe",
  "component_id": "123"
}
```

---

## Magic Links

For simple chatbots that don't support tool calling, you can simply output a link that users click to see the generated UI.

**Format:**
`https://your-spark-domain.com/api/a2a/render?prompt=YOUR_PROMPT`

**Example:**
> "I can generate that chart for you. [Click here to view Sales Chart](https://spark.domain/api/a2a/render?prompt=bar+chart+of+sales)"


