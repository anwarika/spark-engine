from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from app.services.llm import LLMService
from app.services.llm_gateway import LLMConfig
from app.services.registry import RegistryService
from app.services.compiler import ComponentCompiler
from app.services.validator import CodeValidator
from app.database import get_storage
from app.middleware.auth import get_tenant_id, get_user_id
import datetime
import json
import logging
import time
from urllib.parse import quote

logger = logging.getLogger(__name__)
router = APIRouter()

llm_service = LLMService()
registry_service = RegistryService()
compiler = ComponentCompiler()
validator = CodeValidator()


class A2AGenerateRequest(BaseModel):
    prompt: str
    data_context: Optional[Dict[str, Any]] = None
    style_context: Optional[Dict[str, Any]] = None
    template_hint: Optional[str] = None
    theme: str = "light"
    provider_config: Optional[Dict[str, Any]] = None  # legacy
    llm_config: Optional[LLMConfig] = None  # per-request LLM override


class A2AResponse(BaseModel):
    status: str  # "success", "needs_info", "error"
    microapp_url: Optional[str] = None  # legacy
    component_id: Optional[str] = None
    render_url: Optional[str] = None
    iframe_url: Optional[str] = None
    embed_html: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    missing_info: Optional[Dict[str, Any]] = None
    message: Optional[str] = None

@router.post("/generate", response_model=A2AResponse)
async def generate_microapp(request: Request, body: A2AGenerateRequest):
    tenant_id = get_tenant_id(request)
    user_id = get_user_id(request)
    storage = get_storage()
    
    # 1. Fetch Registry Context
    registry_context = await registry_service.get_registry_context(tenant_id)
    
    # 2. Analyze Phase: Does LLM have enough info?
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
    
    provider_config = body.llm_config.model_dump(exclude_none=True) if body.llm_config else body.provider_config

    try:
        analysis_response = await llm_service.analyze(
            analysis_messages,
            analysis_system_prompt,
            provider_config=provider_config,
            temperature=0.1,
        )
        try:
            analysis = json.loads(analysis_response.content)
        except:
            logger.warning("Failed to parse analysis JSON")
            analysis = {"status": "sufficient"} 
            
        if analysis.get("status") == "missing_data":
            return A2AResponse(
                status="needs_info",
                missing_info=analysis.get("missing_schema"),
                message=analysis.get("reasoning")
            )
            
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
    
    # 3. Generation Phase
    context_str = ""
    if body.data_context:
        context_str += f"\nDATA CONTEXT: {json.dumps(body.data_context)}\n"
    if registry_context:
        context_str += f"\n{registry_context}\n"
        
    full_prompt = f"{body.prompt}\n{context_str}"
    
    response = await llm_service.generate_response(
        full_prompt,
        provider_config=provider_config,
    )
    
    if response.type != "component":
        return A2AResponse(
            status="error",
            message=response.content 
        )
        
    # 4. Compilation & Save
    compile_start = time.time()
    code_hash = ComponentCompiler.compute_hash(response.content)
    compilation_result = await compiler.compile(response.content, code_hash)
    compile_time_ms = int((time.time() - compile_start) * 1000)
    
    if not compilation_result.success:
        return A2AResponse(status="error", message=f"Compilation failed: {compilation_result.error}")

    component_name = f"A2A-Gen-{datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
    description = json.dumps({"prompt": body.prompt, "source": "a2a"})
    
    try:
        component_id = await storage.create_component({
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
        })
    except Exception as e:
        logger.error(f"Failed to save component: {e}")
        return A2AResponse(status="error", message="Failed to save component")
    
    base = str(request.base_url).rstrip("/")
    iframe_url = f"{base}/api/components/{component_id}/iframe"
    embed_html = f'<iframe src="{iframe_url}" sandbox="allow-scripts allow-same-origin"></iframe>'

    return A2AResponse(
        status="success",
        component_id=str(component_id),
        microapp_url=iframe_url,
        render_url=f"{base}/api/a2a/render?prompt={quote(body.prompt[:200])}",
        iframe_url=iframe_url,
        embed_html=embed_html,
        metadata={
            "template_used": body.template_hint or "custom",
            "compile_time_ms": compile_time_ms,
            "bundle_size_bytes": compilation_result.bundle_size,
            "cache_hit": False,
        },
    )

@router.get("/render", response_class=HTMLResponse)
async def quick_render(request: Request, prompt: str):
    """
    Magic Link Endpoint: Generates and returns a microapp wrapper HTML directly.
    Usage: GET /api/a2a/render?prompt=Visualize+sales+data
    """
    try:
        # Generate Component
        gen_req = A2AGenerateRequest(prompt=prompt)
        result = await generate_microapp(request, gen_req)
        
        if result.status == "success" and result.microapp_url:
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
