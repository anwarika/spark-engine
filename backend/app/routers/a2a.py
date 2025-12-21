from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from app.services.llm import LLMService
from app.services.registry import RegistryService
from app.services.compiler import ComponentCompiler
from app.services.validator import CodeValidator
from app.database import get_supabase
from app.middleware.auth import get_tenant_id, get_user_id
import datetime
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

llm_service = LLMService()
registry_service = RegistryService()
compiler = ComponentCompiler()
validator = CodeValidator()

class A2AGenerateRequest(BaseModel):
    prompt: str
    data_context: Optional[Dict[str, Any]] = None # The actual data or schema
    style_context: Optional[Dict[str, Any]] = None
    provider_config: Optional[Dict[str, Any]] = None # BYO-LLM config

class A2AResponse(BaseModel):
    status: str # "success", "needs_info", "error"
    microapp_url: Optional[str] = None
    component_id: Optional[str] = None
    missing_info: Optional[Dict[str, Any]] = None # Schema of missing data
    message: Optional[str] = None

@router.post("/generate", response_model=A2AResponse)
async def generate_microapp(request: Request, body: A2AGenerateRequest):
    tenant_id = get_tenant_id(request)
    user_id = get_user_id(request)
    
    # 1. Fetch Registry Context
    registry_context = await registry_service.get_registry_context(tenant_id)
    
    # 2. Analyze Phase: Does LLM have enough info?
    # We construct a specific prompt for analysis
    analysis_system_prompt = """You are an A2A (Agent-to-Agent) negotiation engine.
Your goal is to determine if the provided data context is sufficient to build the requested microapp.

Input:
- User Prompt
- Data Context (Schema/Samples)

Output (JSON):
{
  "status": "sufficient" | "missing_data",
  "missing_schema": { ... JSON Schema of needed data ... } (only if missing_data),
  "reasoning": "Explanation"
}

If the user request implies visualization (chart, table) but NO data is provided, status is "missing_data".
If the user request is generic ("make a sales chart") and data is missing, define the schema you need.
If the user provides data (e.g. "sales": [...]), status is "sufficient".
"""
    
    analysis_messages = [
        {"role": "user", "content": f"Prompt: {body.prompt}\nData Context: {json.dumps(body.data_context or {})}"}
    ]
    
    # We reuse LLMService but might need a raw generation method or just use the standard one
    # For now, let's use the standard generate_response but we need to override the system prompt
    # The current LLMService is tightly coupled to component generation.
    # We'll do a direct call via the provider for this analysis step.
    
    try:
        analysis_response = await llm_service.provider.generate_response(
            analysis_messages, 
            analysis_system_prompt,
            temperature=0.1
        )
        # Parse the text response (BaseLLMProvider returns ChatResponse object)
        try:
            analysis = json.loads(analysis_response.content)
        except:
            # Fallback if not valid JSON
            logger.warning("Failed to parse analysis JSON")
            analysis = {"status": "sufficient"} # Optimistic fallback
            
        if analysis.get("status") == "missing_data":
            return A2AResponse(
                status="needs_info",
                missing_info=analysis.get("missing_schema"),
                message=analysis.get("reasoning")
            )
            
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        # Proceed to generation as fallback
    
    # 3. Generation Phase
    # Inject data context into the system prompt or user message
    context_str = ""
    if body.data_context:
        context_str += f"\nDATA CONTEXT: {json.dumps(body.data_context)}\n"
    if registry_context:
        context_str += f"\n{registry_context}\n"
        
    full_prompt = f"{body.prompt}\n{context_str}"
    
    response = await llm_service.generate_response(
        full_prompt, 
        provider_config=body.provider_config
    )
    
    if response.type != "component":
        return A2AResponse(
            status="error",
            message=response.content # Return the text response as message
        )
        
    # 4. Compilation & Save (Reuse logic from chat.py - ideally refactored into service)
    # For brevity, duplicating critical save logic here
    code_hash = ComponentCompiler.compute_hash(response.content)
    compilation_result = await compiler.compile(response.content, code_hash)
    
    if not compilation_result.success:
        return A2AResponse(status="error", message=f"Compilation failed: {compilation_result.error}")

    supabase = get_supabase()
    try:
        supabase.rpc('set_config', {'setting': 'app.tenant_id', 'value': tenant_id}).execute()
    except:
        pass

    component_name = f"A2A-Gen-{datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
    description = json.dumps({"prompt": body.prompt, "source": "a2a"})
    
    res = supabase.table("components").insert({
        "tenant_id": tenant_id,
        "user_id": user_id,
        "name": component_name,
        "description": description,
        "solidjs_code": response.content,
        "code_hash": code_hash,
        "validated": True,
        "compiled": True,
        "compiled_bundle": compilation_result.bundle,
        "bundle_size_bytes": compilation_result.bundle_size,
        "status": "active"
    }).execute()
    
    component_id = res.data[0]["id"]
    
    # Construct Render URL
    # Assuming request.base_url is correct, or use a configured public URL
    render_url = f"{request.base_url}api/components/{component_id}/iframe"
    
    return A2AResponse(
        status="success",
        component_id=component_id,
        microapp_url=render_url
    )

@router.get("/render", response_class=HTMLResponse)
async def quick_render(request: Request, prompt: str):
    """
    Magic Link Endpoint: Generates and returns a microapp wrapper HTML directly.
    Usage: GET /api/a2a/render?prompt=Visualize+sales+data
    """
    # 1. Reuse generation logic (simplified)
    # Note: We skip the "Negotiation" phase here for speed and simplicity.
    # It assumes the prompt + implicit mocks are enough.
    
    try:
        # Generate Component
        gen_req = A2AGenerateRequest(prompt=prompt)
        result = await generate_microapp(request, gen_req)
        
        if result.status == "success" and result.microapp_url:
            # Return a wrapper page that embeds the iframe
            # We use absolute URL for the iframe src
            iframe_src = str(result.microapp_url)
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Spark MicroApp</title>
                <style>
                    body, html {{ margin: 0; padding: 0; height: 100%; overflow: hidden; font-family: system-ui, sans-serif; }}
                    iframe {{ width: 100%; height: 100%; border: none; }}
                    .header {{ padding: 10px; background: #f0f0f0; border-bottom: 1px solid #ccc; font-size: 12px; color: #666; display: flex; justify-content: space-between; }}
                    .logo {{ font-weight: bold; color: #333; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <span class="logo">⚡ Spark AI</span>
                    <span>Prompt: {prompt}</span>
                </div>
                <iframe src="{iframe_src}" sandbox="allow-scripts allow-same-origin"></iframe>
            </body>
            </html>
            """
            return HTMLResponse(content=html_content)
        elif result.status == "needs_info":
             return HTMLResponse(content=f"<h1>Need More Info</h1><p>{result.message}</p><pre>{json.dumps(result.missing_info, indent=2)}</pre>", status_code=400)
        else:
            return HTMLResponse(content=f"<h1>Error</h1><p>{result.message}</p>", status_code=500)
            
    except Exception as e:
        logger.error(f"Magic link failed: {e}")
        return HTMLResponse(content=f"<h1>System Error</h1><p>{str(e)}</p>", status_code=500)
