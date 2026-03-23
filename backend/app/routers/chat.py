from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from app.models import ChatMessage, ChatResponse
from app.services.llm import LLMService
from app.services.validator import CodeValidator
from app.services.compiler import ComponentCompiler
from app.services.cag import CAGService, increment_reuse_count
from app.database import get_storage
from app.middleware.auth import get_tenant_id, get_user_id
import logging
import uuid
import time
import json
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)
router = APIRouter()

llm_service = LLMService()
validator = CodeValidator()
compiler = ComponentCompiler()
cag_service = CAGService()

MAX_EDIT_RETRIES = 2  # 1 initial attempt + 1 retry on validation/compile error

def _sse(event: str, data: dict) -> str:
    # SSE format: event + data + blank line
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _generate_edit_with_retry(
    instruction: str,
    existing_code: str,
    conversation_history: list,
    llm_config=None,
) -> tuple:
    """Run generate_edit_response with one automatic retry on validate/compile failure.

    Returns (llm_response, validation_result, compilation_result, last_error_message).
    On success, last_error_message is None.
    """
    last_error: str | None = None
    for attempt in range(MAX_EDIT_RETRIES):
        llm_response = await llm_service.generate_edit_response(
            instruction,
            existing_code,
            conversation_history,
            llm_config=llm_config,
            prior_error=last_error,
        )
        if llm_response.type != "component":
            return llm_response, None, None, None

        validation_result = validator.validate(llm_response.content)
        if not validation_result.valid:
            last_error = "Validation errors:\n" + "\n".join(validation_result.errors)
            logger.warning(f"Edit attempt {attempt + 1} validation failed; retrying: {last_error[:120]}")
            if attempt < MAX_EDIT_RETRIES - 1:
                continue
            return llm_response, validation_result, None, last_error

        code_hash = ComponentCompiler.compute_hash(llm_response.content)
        compilation_result = await compiler.compile(llm_response.content, code_hash)
        if not compilation_result.success:
            last_error = f"Compilation error: {compilation_result.error}"
            logger.warning(f"Edit attempt {attempt + 1} compilation failed; retrying: {last_error[:120]}")
            if attempt < MAX_EDIT_RETRIES - 1:
                continue
            return llm_response, validation_result, compilation_result, last_error

        return llm_response, validation_result, compilation_result, None

    # Should not reach here
    return llm_response, None, None, last_error


@router.post("/message")
async def chat_message(message: ChatMessage, request: Request):
    # Start timing - request to render
    request_start_time = time.time()
    timing_breakdown = {
        "db_session_ms": 0,
        "db_history_ms": 0,
        "llm_generation_ms": 0,
        "validation_ms": 0,
        "compilation_ms": 0,
        "db_save_component_ms": 0,
        "db_save_message_ms": 0,
        "total_ms": 0
    }
    
    tenant_id = get_tenant_id(request)
    user_id = get_user_id(request)
    storage = get_storage()

    # Time database session operations
    db_start = time.time()
    try:
        session_db_id = await storage.get_or_create_session(tenant_id, user_id, message.session_id)
        await storage.update_session_activity(session_db_id)
    except Exception as e:
        logger.error(f"Session DB error: {e}")
        raise HTTPException(status_code=500, detail="Database session error")
        
    timing_breakdown["db_session_ms"] = round((time.time() - db_start) * 1000, 2)

    # Time history fetch
    history_start = time.time()
    try:
        history_data = await storage.get_chat_history(session_db_id)
        conversation_history = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in history_data
        ]
    except Exception as e:
        logger.warning(f"Failed to fetch history: {e}")
        conversation_history = []
        
    timing_breakdown["db_history_ms"] = round((time.time() - history_start) * 1000, 2)

    # Save user message - non-blocking
    try:
        await storage.save_chat_message(session_db_id, "user", message.message)
    except Exception as e:
        logger.warning(f"Failed to save user message to database: {e}")

    # Iteration mode: component_id provided, edit existing component
    if message.component_id:
        parent_id = message.component_id
        existing_component = await storage.get_component(parent_id, tenant_id)
        if not existing_component:
            raise HTTPException(status_code=404, detail="Component not found for iteration")

        llm_start = time.time()
        # Fix 4: auto-retry on validation/compile error with error context fed back
        llm_response, validation_result, compilation_result, last_error = \
            await _generate_edit_with_retry(
                message.message,
                existing_component["solidjs_code"],
                conversation_history,
            )
        timing_breakdown["llm_generation_ms"] = round((time.time() - llm_start) * 1000, 2)

        component_id = None
        if llm_response.type == "component":
            if last_error:
                error_message = f"Could not generate a valid component after {MAX_EDIT_RETRIES} attempts.\nLast error: {last_error}"
                try:
                    await storage.save_chat_message(
                        session_db_id, "assistant", error_message,
                        llm_model=llm_service.model, reasoning=llm_response.reasoning
                    )
                except Exception as e:
                    logger.warning(f"Failed to save error message: {e}")
                return ChatResponse(type="text", content=error_message, reasoning="Edit failed after retries")

            db_save_start = time.time()
            component_name = f"Component-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
            request_start_timestamp_ms = int(request_start_time * 1000)
            description_with_metadata = json.dumps({
                "text": f"Iteration: {message.message[:100]}",
                "request_start_timestamp_ms": request_start_timestamp_ms,
            })
            generation_metadata = {
                "parent_component_id": parent_id,
                "prompt_original": message.message,
                "template_name": None,
                "data_profile": "ecommerce",
                "reuse_count": 0,
                "source": "iteration",
            }
            code_hash = ComponentCompiler.compute_hash(llm_response.content)
            try:
                component_id = await storage.create_component({
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "name": component_name,
                    "description": description_with_metadata,
                    "solidjs_code": llm_response.content,
                    "code_hash": code_hash,
                    "generation_metadata": json.dumps(generation_metadata),
                    "validated": True,
                    "compiled": True,
                    "compiled_bundle": compilation_result.bundle,
                    "bundle_size_bytes": compilation_result.bundle_size,
                    "status": "active",
                })
            except Exception as e:
                logger.error(f"Failed to create component: {e}")
                raise HTTPException(status_code=500, detail=f"Database component save failed: {e}")
            timing_breakdown["db_save_component_ms"] = round((time.time() - db_save_start) * 1000, 2)

        db_message_start = time.time()
        try:
            await storage.save_chat_message(
                session_db_id, "assistant", llm_response.content,
                component_id=component_id,
                llm_model=llm_service.model,
                reasoning=llm_response.reasoning
            )
        except Exception as e:
            logger.warning(f"Failed to save assistant message to database: {e}")
        timing_breakdown["db_save_message_ms"] = round((time.time() - db_message_start) * 1000, 2)
        timing_breakdown["total_ms"] = round((time.time() - request_start_time) * 1000, 2)

        # In iteration mode, return description only — not the raw code
        display_content = llm_response.reasoning if message.component_id else llm_response.content
        return ChatResponse(
            type=llm_response.type,
            content=display_content,
            component_id=component_id,
            reasoning=llm_response.reasoning,
        )

    # CAG: Check for existing component before LLM generation
    cag_start = time.time()
    content_fingerprint = cag_service.create_fingerprint(
        prompt=message.message,
        template_name=None,  # Will be determined after LLM response
        data_profile="ecommerce"  # Default for now
    )
    
    existing_component = await storage.find_component_by_content_hash(
        tenant_id, 
        content_fingerprint.content_hash
    )
    timing_breakdown["cag_lookup_ms"] = round((time.time() - cag_start) * 1000, 2)

    if existing_component and cag_service.should_reuse(existing_component):
        # Component already exists! Return it without LLM generation
        logger.info(f"CAG HIT: Reusing component {existing_component['id']} for prompt hash {content_fingerprint.content_hash[:12]}")
        
        # Update reuse metadata
        gen_metadata = existing_component.get('generation_metadata', {})
        if isinstance(gen_metadata, str):
            try:
                gen_metadata = json.loads(gen_metadata)
            except:
                gen_metadata = {}
        updated_metadata = increment_reuse_count(gen_metadata)
        
        # Save assistant message referencing the existing component
        try:
            await storage.save_chat_message(
                session_db_id, "assistant", existing_component['solidjs_code'],
                component_id=existing_component['id'],
                llm_model="cag_reuse",
                reasoning=f"Reused existing component (content_hash: {content_fingerprint.content_hash[:12]})"
            )
        except Exception as e:
            logger.warning(f"Failed to save CAG reuse message: {e}")
        
        timing_breakdown["total_ms"] = round((time.time() - request_start_time) * 1000, 2)
        
        # Log CAG metrics
        cag_metrics = {
            "event": "cag_hit",
            "timestamp": datetime.utcnow().isoformat(),
            "tenant_id": tenant_id,
            "user_id": user_id,
            "component_id": existing_component['id'],
            "content_hash": content_fingerprint.content_hash,
            "normalized_prompt": content_fingerprint.normalized_prompt,
            "reuse_count": updated_metadata.get('reuse_count', 1),
            "timing": timing_breakdown
        }
        logger.info(json.dumps(cag_metrics))
        
        return ChatResponse(
            type="component",
            content=existing_component['solidjs_code'],
            component_id=existing_component['id'],
            reasoning=f"Reused existing component (saves ~{timing_breakdown.get('llm_generation_ms', 1500)}ms generation time)",
        )
    
    # CAG MISS: Generate new component
    logger.info(f"CAG MISS: No existing component for hash {content_fingerprint.content_hash[:12]}, generating new")

    # Time LLM generation
    llm_start = time.time()
    llm_response = await llm_service.generate_response(
        message.message,
        conversation_history,
        mode=message.mode,
    )
    timing_breakdown["llm_generation_ms"] = round((time.time() - llm_start) * 1000, 2)

    component_id = None
    compilation_result = None

    if llm_response.type == "component":
        logger.info(f"Validating generated component code (length: {len(llm_response.content)} chars)")
        logger.info(f"Component code:\n{llm_response.content}")
        
        # Time validation
        validation_start = time.time()
        validation_result = validator.validate(llm_response.content)
        timing_breakdown["validation_ms"] = round((time.time() - validation_start) * 1000, 2)

        if not validation_result.valid:
            logger.error(f"Validation failed for code:\n{llm_response.content}")
            error_message = "Component validation failed:\n" + "\n".join(validation_result.errors)
            try:
                await storage.save_chat_message(
                    session_db_id, "assistant", error_message, 
                    llm_model=llm_service.model, reasoning=llm_response.reasoning
                )
            except Exception as e:
                logger.warning(f"Failed to save validation error message to database: {e}")

            return ChatResponse(
                type="text",
                content=error_message,
                reasoning="Validation failed"
            )

        code_hash = ComponentCompiler.compute_hash(llm_response.content)

        # Time compilation (includes its own timing, but we track total here)
        compilation_start = time.time()
        compilation_result = await compiler.compile(llm_response.content, code_hash)
        timing_breakdown["compilation_ms"] = round((time.time() - compilation_start) * 1000, 2)

        if not compilation_result.success:
            error_message = f"Component compilation failed: {compilation_result.error}"
            try:
                await storage.save_chat_message(
                    session_db_id, "assistant", error_message,
                    llm_model=llm_service.model, reasoning=llm_response.reasoning
                )
            except Exception as e:
                logger.warning(f"Failed to save compilation error message to database: {e}")

            return ChatResponse(
                type="text",
                content=error_message,
                reasoning="Compilation failed"
            )

        # Time component save to database
        db_save_start = time.time()
        component_name = f"Component-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        # Store request start time in description for total time calculation
        request_start_timestamp_ms = int(request_start_time * 1000)
        description_with_metadata = json.dumps({
            "text": f"Generated from: {message.message[:100]}",
            "request_start_timestamp_ms": request_start_timestamp_ms
        })
        
        # CAG: Store content hash and metadata
        generation_metadata = {
            "prompt_original": message.message,
            "template_name": None,  # Could extract from LLM response if available
            "data_profile": "ecommerce",
            "reuse_count": 0,
            "original_component_id": None  # This is the original
        }
        
        try:
            component_id = await storage.create_component({
                "tenant_id": tenant_id,
                "user_id": user_id,
                "name": component_name,
                "description": description_with_metadata,
                "solidjs_code": llm_response.content,
                "code_hash": code_hash,
                "content_hash": content_fingerprint.content_hash,
                "prompt_normalized": content_fingerprint.normalized_prompt,
                "generation_metadata": json.dumps(generation_metadata),
                "validated": True,
                "compiled": True,
                "compiled_bundle": compilation_result.bundle,
                "bundle_size_bytes": compilation_result.bundle_size,
                "status": "active"
            })
        except Exception as e:
            logger.error(f"Failed to create component: {e}")
            raise HTTPException(status_code=500, detail=f"Database component save failed: {e}")
            
        timing_breakdown["db_save_component_ms"] = round((time.time() - db_save_start) * 1000, 2)

        logger.info(
            f"Component generated: id={component_id}, size={compilation_result.bundle_size}, "
            f"compile_time={compilation_result.compile_time_ms}ms"
        )

    # Save assistant response - non-blocking
    db_message_start = time.time()
    try:
        await storage.save_chat_message(
            session_db_id, "assistant", llm_response.content,
            component_id=component_id,
            llm_model=llm_service.model,
            reasoning=llm_response.reasoning
        )
    except Exception as e:
        logger.warning(f"Failed to save assistant message to database: {e}")
    timing_breakdown["db_save_message_ms"] = round((time.time() - db_message_start) * 1000, 2)

    # Calculate total time
    timing_breakdown["total_ms"] = round((time.time() - request_start_time) * 1000, 2)

    # Determine cache strategy used
    cache_strategy = "cag_miss_llm_generated"
    if llm_response.type == "component" and compilation_result:
        if compilation_result.compile_time_ms == 0:
            cache_strategy = "cag_miss_bundle_cached"
        else:
            cache_strategy = "cag_miss_compiled_fresh"
    
    # Calculate optimization score (smaller is better)
    optimization_score = None
    if llm_response.type == "component" and compilation_result:
        target_size = 5120  # 5KB target
        optimization_score = round(compilation_result.bundle_size / target_size, 2)
    
    # Log comprehensive performance metrics
    metrics = {
        "event": "micro_app_created" if llm_response.type == "component" else "chat_response",
        "timestamp": datetime.utcnow().isoformat(),
        "tenant_id": tenant_id,
        "user_id": user_id,
        "session_id": message.session_id,
        "component_id": component_id,
        "response_type": llm_response.type,
        "cache_strategy": cache_strategy,
        "timing": timing_breakdown,
        "component_metrics": {
            "bundle_size_bytes": compilation_result.bundle_size,
            "code_length_chars": len(llm_response.content),
            "bundle_cache_hit": compilation_result.compile_time_ms == 0,
            "optimization_score": optimization_score
        } if llm_response.type == "component" and compilation_result else None,
        "cag_metrics": {
            "content_hash": content_fingerprint.content_hash,
            "normalized_prompt": content_fingerprint.normalized_prompt,
            "cag_hit": False,  # This was a miss
            "cag_lookup_ms": timing_breakdown.get("cag_lookup_ms", 0)
        },
        "caching": {
            "cag_available": True,
            "prompt_cache_available": True,
            "data_cache_available": True,
            "bundle_cached": compilation_result.compile_time_ms == 0 if compilation_result else False
        }
    }
    
    logger.info(json.dumps(metrics))

    return ChatResponse(
        type=llm_response.type,
        content=llm_response.content,
        component_id=component_id,
        reasoning=llm_response.reasoning,
    )


@router.post("/message/stream")
async def chat_message_stream(message: ChatMessage, request: Request):
    """
    Stream generation progress via Server-Sent Events (SSE).
    """

    async def event_gen():
        request_start_time = time.time()
        timing_breakdown = {
            "db_session_ms": 0,
            "db_history_ms": 0,
            "llm_generation_ms": 0,
            "validation_ms": 0,
            "compilation_ms": 0,
            "db_save_component_ms": 0,
            "db_save_message_ms": 0,
            "total_ms": 0
        }

        try:
            yield _sse("progress", {"step": "start", "status": "start"})

            tenant_id = get_tenant_id(request)
            user_id = get_user_id(request)
            storage = get_storage()

            # Session upsert
            yield _sse("progress", {"step": "db_session", "status": "start"})
            db_start = time.time()
            try:
                session_db_id = await storage.get_or_create_session(tenant_id, user_id, message.session_id)
                await storage.update_session_activity(session_db_id)
            except Exception as e:
                 logger.error(f"Session error: {e}")
                 yield _sse("error", {"message": "Database session error"})
                 return

            timing_breakdown["db_session_ms"] = round((time.time() - db_start) * 1000, 2)
            yield _sse("progress", {"step": "db_session", "status": "done", "ms": timing_breakdown["db_session_ms"]})

            # History fetch
            yield _sse("progress", {"step": "db_history", "status": "start"})
            history_start = time.time()
            try:
                history_data = await storage.get_chat_history(session_db_id)
                conversation_history = [
                    {"role": msg["role"], "content": msg["content"]}
                    for msg in history_data
                ]
            except Exception:
                conversation_history = []
                
            timing_breakdown["db_history_ms"] = round((time.time() - history_start) * 1000, 2)
            yield _sse("progress", {"step": "db_history", "status": "done", "ms": timing_breakdown["db_history_ms"]})

            # Save user message (best-effort)
            try:
                await storage.save_chat_message(session_db_id, "user", message.message)
            except Exception as e:
                logger.warning(f"Failed to save user message to database: {e}")

            component_id = None
            compilation_result = None
            parent_component_id = None

            # Iteration mode: component_id provided, edit existing component
            if message.component_id:
                parent_component_id = message.component_id
                existing_component = await storage.get_component(parent_component_id, tenant_id)
                if not existing_component:
                    yield _sse("error", {"message": "Component not found for iteration"})
                    return

                yield _sse("progress", {"step": "llm_generation", "status": "start"})
                llm_start = time.time()
                # Fix 4: auto-retry with error context fed back to the LLM
                llm_response, _val_result, compilation_result, last_error = \
                    await _generate_edit_with_retry(
                        message.message,
                        existing_component["solidjs_code"],
                        conversation_history,
                    )
                timing_breakdown["llm_generation_ms"] = round((time.time() - llm_start) * 1000, 2)
                yield _sse("progress", {"step": "llm_generation", "status": "done", "ms": timing_breakdown["llm_generation_ms"]})

                if llm_response.type == "component" and last_error:
                    # All retries exhausted
                    error_message = f"Could not generate a valid component after {MAX_EDIT_RETRIES} attempts.\nLast error: {last_error}"
                    yield _sse("done", {
                        "type": "text",
                        "content": error_message,
                        "reasoning": "Edit failed after retries",
                        "timing": {**timing_breakdown, "total_ms": round((time.time() - request_start_time) * 1000, 2)}
                    })
                    return
            else:
                # New generation
                yield _sse("progress", {"step": "llm_generation", "status": "start"})
                llm_start = time.time()
                llm_response = await llm_service.generate_response(
                    message.message,
                    conversation_history
                )
                timing_breakdown["llm_generation_ms"] = round((time.time() - llm_start) * 1000, 2)
                yield _sse("progress", {"step": "llm_generation", "status": "done", "ms": timing_breakdown["llm_generation_ms"]})
                compilation_result = None

            if llm_response.type == "component":
                if not message.component_id:
                    # New generation path: validate and compile here
                    yield _sse("progress", {"step": "validation", "status": "start"})
                    validation_start = time.time()
                    validation_result = validator.validate(llm_response.content)
                    timing_breakdown["validation_ms"] = round((time.time() - validation_start) * 1000, 2)
                    if not validation_result.valid:
                        error_message = "Component validation failed:\n" + "\n".join(validation_result.errors)
                        yield _sse("progress", {"step": "validation", "status": "error", "ms": timing_breakdown["validation_ms"]})
                        yield _sse("done", {
                            "type": "text",
                            "content": error_message,
                            "reasoning": "Validation failed",
                            "timing": {**timing_breakdown, "total_ms": round((time.time() - request_start_time) * 1000, 2)}
                        })
                        return
                    yield _sse("progress", {"step": "validation", "status": "done", "ms": timing_breakdown["validation_ms"]})

                    code_hash = ComponentCompiler.compute_hash(llm_response.content)

                    yield _sse("progress", {"step": "compilation", "status": "start"})
                    compilation_start = time.time()
                    compilation_result = await compiler.compile(llm_response.content, code_hash)
                    timing_breakdown["compilation_ms"] = round((time.time() - compilation_start) * 1000, 2)
                    if not compilation_result.success:
                        error_message = f"Component compilation failed: {compilation_result.error}"
                        yield _sse("progress", {"step": "compilation", "status": "error", "ms": timing_breakdown["compilation_ms"]})
                        yield _sse("done", {
                            "type": "text",
                            "content": error_message,
                            "reasoning": "Compilation failed",
                            "timing": {**timing_breakdown, "total_ms": round((time.time() - request_start_time) * 1000, 2)}
                        })
                        return
                    yield _sse("progress", {"step": "compilation", "status": "done", "ms": timing_breakdown["compilation_ms"]})
                else:
                    # Iteration path: validate/compile already done by _generate_edit_with_retry
                    # Emit progress steps as done for UI consistency
                    yield _sse("progress", {"step": "validation", "status": "done", "ms": 0})
                    yield _sse("progress", {"step": "compilation", "status": "done", "ms": 0})
                    code_hash = ComponentCompiler.compute_hash(llm_response.content)

                # Save component (so we can emit microapp_ready ASAP)
                yield _sse("progress", {"step": "db_save_component", "status": "start"})
                db_save_start = time.time()
                component_name = f"Component-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
                request_start_timestamp_ms = int(request_start_time * 1000)
                description_with_metadata = json.dumps({
                    "text": f"Iteration: {message.message[:100]}" if parent_component_id else f"Generated from: {message.message[:100]}",
                    "request_start_timestamp_ms": request_start_timestamp_ms
                })
                create_payload = {
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "name": component_name,
                    "description": description_with_metadata,
                    "solidjs_code": llm_response.content,
                    "code_hash": code_hash,
                    "validated": True,
                    "compiled": True,
                    "compiled_bundle": compilation_result.bundle,
                    "bundle_size_bytes": compilation_result.bundle_size,
                    "status": "active"
                }
                if parent_component_id:
                    create_payload["generation_metadata"] = json.dumps({
                        "parent_component_id": parent_component_id,
                        "prompt_original": message.message,
                        "source": "iteration",
                    })
                try:
                    component_id = await storage.create_component(create_payload)
                except Exception as e:
                     logger.error(f"Failed to save component: {e}")
                     yield _sse("error", {"message": "Failed to save component"})
                     return
                
                timing_breakdown["db_save_component_ms"] = round((time.time() - db_save_start) * 1000, 2)
                yield _sse("progress", {"step": "db_save_component", "status": "done", "ms": timing_breakdown["db_save_component_ms"]})
                microapp_data = {"component_id": component_id}
                if parent_component_id:
                    microapp_data["parent_component_id"] = parent_component_id
                yield _sse("microapp_ready", microapp_data)

            # Save assistant response (best-effort)
            yield _sse("progress", {"step": "db_save_message", "status": "start"})
            db_message_start = time.time()
            try:
                await storage.save_chat_message(
                    session_db_id, "assistant", llm_response.content,
                    component_id=component_id,
                    llm_model=llm_service.model,
                    reasoning=llm_response.reasoning
                )
            except Exception as e:
                logger.warning(f"Failed to save assistant message to database: {e}")
            timing_breakdown["db_save_message_ms"] = round((time.time() - db_message_start) * 1000, 2)
            yield _sse("progress", {"step": "db_save_message", "status": "done", "ms": timing_breakdown["db_save_message_ms"]})

            timing_breakdown["total_ms"] = round((time.time() - request_start_time) * 1000, 2)
            # In iteration mode, show description only — not the raw code
            display_content = llm_response.reasoning if parent_component_id else llm_response.content
            yield _sse("done", {
                "type": llm_response.type,
                "content": display_content,
                "component_id": component_id,
                "reasoning": llm_response.reasoning,
                "timing": timing_breakdown
            })

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.exception("Streaming chat endpoint failed")
            yield _sse("error", {"message": str(e)})

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
