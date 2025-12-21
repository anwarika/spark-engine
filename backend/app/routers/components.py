from fastapi import APIRouter, Request, HTTPException, Response
from app.models import ComponentFeedback
from app.database import get_supabase
from app.middleware.auth import get_tenant_id, get_user_id
from typing import Optional
import logging
import json
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter()

from app.services.mock_data import MockSpec, generate_mock_dataset


@router.get("")
async def list_components(
    request: Request,
    limit: int = 20,
    offset: int = 0,
    status: Optional[str] = "active"
):
    tenant_id = get_tenant_id(request)
    supabase = get_supabase()

    try:
        supabase.rpc(
            'set_config',
            {'setting': 'app.tenant_id', 'value': tenant_id}
        ).execute()
    except:
        pass

    query = supabase.table("components").select(
        "id, name, description, version, bundle_size_bytes, status, created_at, updated_at"
    ).eq("tenant_id", tenant_id)

    if status:
        query = query.eq("status", status)

    result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()

    return {
        "components": result.data,
        "total": len(result.data),
        "limit": limit,
        "offset": offset
    }


@router.get("/{component_id}")
async def get_component(component_id: str, request: Request):
    tenant_id = get_tenant_id(request)
    supabase = get_supabase()

    try:
        supabase.rpc(
            'set_config',
            {'setting': 'app.tenant_id', 'value': tenant_id}
        ).execute()
    except:
        pass

    result = supabase.table("components").select("*").eq(
        "id", component_id
    ).eq("tenant_id", tenant_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Component not found")

    return result.data[0]


@router.get("/{component_id}/artifact")
async def get_component_artifact(component_id: str, request: Request):
    tenant_id = get_tenant_id(request)
    supabase = get_supabase()

    try:
        supabase.rpc(
            'set_config',
            {'setting': 'app.tenant_id', 'value': tenant_id}
        ).execute()
    except:
        pass

    result = supabase.table("components").select(
        "compiled_bundle, name"
    ).eq("id", component_id).eq("tenant_id", tenant_id).execute()

    if not result.data or not result.data[0].get("compiled_bundle"):
        raise HTTPException(status_code=404, detail="Artifact not found")

    return Response(
        content=result.data[0]["compiled_bundle"],
        media_type="application/javascript",
        headers={
            "Content-Disposition": f"inline; filename=\"{result.data[0]['name']}.js\"",
            "Cache-Control": "public, max-age=3600"
        }
    )


@router.get("/{component_id}/iframe")
async def get_component_iframe(component_id: str, request: Request):
    tenant_id = get_tenant_id(request)
    user_id = get_user_id(request)
    
    # Get component creation timestamp for total time calculation
    supabase = get_supabase()
    try:
        supabase.rpc(
            'set_config',
            {'setting': 'app.tenant_id', 'value': tenant_id}
        ).execute()
    except:
        pass
    
    component_result = supabase.table("components").select("description, created_at").eq(
        "id", component_id
    ).eq("tenant_id", tenant_id).execute()
    
    # Try to get request_start_timestamp from description metadata
    request_start_timestamp = None
    if component_result.data:
        description = component_result.data[0].get("description", "")
        try:
            # Try to parse as JSON metadata
            desc_data = json.loads(description)
            if isinstance(desc_data, dict) and "request_start_timestamp_ms" in desc_data:
                request_start_timestamp = desc_data["request_start_timestamp_ms"]
        except (json.JSONDecodeError, TypeError):
            # Fallback to created_at if description is not JSON
            component_created_at = component_result.data[0].get("created_at")
            if component_created_at:
                try:
                    created_dt = datetime.fromisoformat(component_created_at.replace('Z', '+00:00'))
                    request_start_timestamp = int(created_dt.timestamp() * 1000)
                except Exception as e:
                    logger.warning(f"Failed to parse component created_at: {e}")
    
    component_created_timestamp = request_start_timestamp

    iframe_html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://esm.sh https://cdn.tailwindcss.com; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdn.tailwindcss.com; connect-src 'self'; img-src 'self' data: https:; font-src 'self' https://cdn.jsdelivr.net;">
  <link href="https://cdn.jsdelivr.net/npm/daisyui@4.12.10/dist/full.min.css" rel="stylesheet">
  <script src="https://cdn.tailwindcss.com"></script>
  <title>Micro App</title>
  <style>
    body {{ margin: 0; padding: 0; }}
    #app {{ min-height: 100vh; }}
  </style>
</head>
<body>
  <div id="app"></div>
  <script type="importmap">
  {{
    "imports": {{
      "solid-js": "https://esm.sh/solid-js@1.8.7",
      "solid-js/web": "https://esm.sh/solid-js@1.8.7/web",
      "solid-js/store": "https://esm.sh/solid-js@1.8.7/store"
    }}
  }}
  </script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
  <script>
    // Set up Chart.js globally
    window.Chart = window.Chart || Chart;
    
    // Set up ApexCharts globals (for future use)
    window.Apex = window.Apex || {{}}; 
    if (!Array.isArray(window.Apex._chartInstances)) {{
      window.Apex._chartInstances = [];
    }}
  </script>
  <script>
    // Global error handler
    window.onerror = function(msg, url, line, col, error) {{
      console.error('Error:', msg, 'at', url, line, col, error);
      const app = document.getElementById('app');
      if (app) {{
        app.innerHTML = '<div style="padding: 20px; color: red;">Error: ' + msg + '</div>';
      }}
      return false;
    }};
    
    // Unhandled promise rejection handler
    window.addEventListener('unhandledrejection', function(event) {{
      console.error('Unhandled promise rejection:', event.reason);
      const app = document.getElementById('app');
      if (app) {{
        app.innerHTML = '<div style="padding: 20px; color: red;">Promise Error: ' + event.reason + '</div>';
      }}
    }});
    
    // Component environment
    window.__COMPONENT_TOKEN = 'placeholder-token';
    window.__COMPONENT_ID = '{component_id}';
    window.__TENANT_ID = '{tenant_id}';
    window.__USER_ID = '{user_id}';
    window.__API_BASE = window.location.origin;
    window.__COMPONENT_CREATED_AT = {component_created_timestamp if component_created_timestamp else 'null'};
    
    // PostMessage handler for A2A communication
    window.addEventListener('message', (event) => {
        // Handle incoming messages from parent
        // console.log('Received message from parent:', event.data);
    });

    // Helper to send events to parent
    window.sendToParent = (type, payload) => {
        if (window.parent && window.parent !== window) {
            window.parent.postMessage({
                type: type,
                payload: payload,
                componentId: window.__COMPONENT_ID
            }, '*');
        }
    };
    
    console.log('Component environment initialized:', {{
      componentId: window.__COMPONENT_ID,
      tenantId: window.__TENANT_ID,
      userId: window.__USER_ID,
      apiBase: window.__API_BASE
    }});
  </script>
  <script type="module">
    // Performance timing - mark when iframe starts loading
    if (window.performance && window.performance.mark) {{
      performance.mark('component-iframe-start');
    }}
    
    // Import SolidJS render and the component module
    import {{ render }} from 'solid-js/web';
    
    try {{
      // Dynamically import the component artifact (ESM module)
      const componentModule = await import('/api/components/{component_id}/artifact');
      
      if (window.performance && window.performance.mark) {{
        performance.mark('component-artifact-loaded');
      }}
      
      console.log('Component module loaded:', componentModule);
      
      // Get the default export (the component function)
      const componentFunc = componentModule.default;
      
      if (!componentFunc) {{
        throw new Error('No default export found in component module');
      }}
      
      if (window.performance && window.performance.mark) {{
        performance.mark('component-render-ready');
      }}
      
      const root = document.getElementById('app');
      
      // Mark render start
      if (window.performance && window.performance.mark) {{
        performance.mark('component-render-start');
      }}
      
      // Render the component
      render(componentFunc, root);
      
      // Mark render complete
      if (window.performance && window.performance.mark) {{
        performance.mark('component-render-complete');
        
        // Measure timing
        try {{
          performance.measure('component-artifact-load', 'component-iframe-start', 'component-artifact-loaded');
          performance.measure('component-render-setup', 'component-artifact-loaded', 'component-render-ready');
          performance.measure('component-render-exec', 'component-render-ready', 'component-render-complete');
          performance.measure('component-total-render', 'component-iframe-start', 'component-render-complete');
          
          // Log render metrics
          const measures = performance.getEntriesByType('measure');
          const renderMetrics = {{
            component_id: window.__COMPONENT_ID,
            timing: {{}}
          }};
          
          measures.forEach(measure => {{
            if (measure.name.startsWith('component-')) {{
              renderMetrics.timing[measure.name] = Math.round(measure.duration * 100) / 100;
            }}
          }});
          
          // Calculate total time from request to render
          if (window.__COMPONENT_CREATED_AT) {{
            const renderCompleteTime = Date.now();
            const totalTimeMs = renderCompleteTime - window.__COMPONENT_CREATED_AT;
            renderMetrics.timing['total-request-to-render'] = Math.round(totalTimeMs * 100) / 100;
            console.log('Total time (request to render):', totalTimeMs, 'ms');
          }}
          
          console.log('Component render metrics:', JSON.stringify(renderMetrics));
          
          // Send metrics to backend (non-blocking)
          fetch('/api/components/' + window.__COMPONENT_ID + '/render-metrics', {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify(renderMetrics)
          }}).catch(err => console.warn('Failed to send render metrics:', err));
        }} catch (e) {{
          console.warn('Performance measurement failed:', e);
        }}
      }}
      
      console.log('Component rendered successfully');
      
    }} catch (error) {{
      console.error('Failed to load or render component:', error);
      const app = document.getElementById('app');
      if (app) {{
        app.innerHTML = '<div style="padding: 20px; color: red;">Failed to load component: ' + error.message + '</div>';
      }}
    }}
  </script>
</body>
</html>"""

    return Response(
        content=iframe_html,
        media_type="text/html"
    )


@router.post("/{component_id}/data")
async def get_component_data(component_id: str, request: Request, body: dict = None):
    tenant_id = get_tenant_id(request)
    user_id = get_user_id(request)

    logger.info(f"Data request received: component={component_id}, tenant={tenant_id}, user={user_id}, body={body}")
    logger.info(f"Request method: {request.method}, URL: {request.url}")

    # Optional: generate large, deterministic datasets for dashboard/latency testing
    # Request body example:
    # { "mock": { "profile": "ecommerce", "scale": "large", "seed": 42, "days": 365, "latency_ms": 150 } }
    try:
        mock_req = (body or {}).get("mock") if isinstance(body, dict) else None
    except Exception:
        mock_req = None

    if isinstance(mock_req, dict):
        # Generate cache key from mock spec
        profile = str(mock_req.get("profile", "ecommerce") or "ecommerce")
        scale = str(mock_req.get("scale", "medium") or "medium")
        seed = int(mock_req.get("seed", 1) or 1)
        days = int(mock_req.get("days", 180) or 180)
        
        cache_key = f"mock:{profile}:{scale}:{seed}:{days}"
        
        # Check cache
        from app.database import get_redis
        redis = await get_redis()
        if redis:
            try:
                cached_data = await redis.get(cache_key)
                if cached_data:
                    logger.info(f"Mock data cache HIT for key: {cache_key}")
                    data = json.loads(cached_data)
                    data["meta"]["requested_by"] = {
                        "tenant_id": tenant_id,
                        "user_id": user_id,
                        "component_id": component_id,
                    }
                    data["meta"]["cache_hit"] = True
                    return data
                logger.debug(f"Mock data cache MISS for key: {cache_key}")
            except Exception as e:
                logger.warning(f"Mock data cache read error: {e}")
        
        # Simulate latency if requested
        latency_ms = int(mock_req.get("latency_ms", 0) or 0)
        if latency_ms and latency_ms > 0:
            await asyncio.sleep(min(latency_ms, 60_000) / 1000.0)

        spec = MockSpec(
            profile=profile,
            scale=scale,
            seed=seed,
            days=days,
        )
        data = generate_mock_dataset(spec)
        data["meta"]["requested_by"] = {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "component_id": component_id,
        }
        data["meta"]["cache_hit"] = False
        
        # Cache the generated data (TTL: 1 hour)
        if redis:
            try:
                await redis.setex(cache_key, 3600, json.dumps(data))
                logger.info(f"Cached mock data with key: {cache_key}")
            except Exception as e:
                logger.warning(f"Mock data cache write error: {e}")
        
        return data

    # Rich mock data for various use cases
    mock_data = {
        # Product catalog
        "products": [
            {"id": 1, "name": "Laptop Pro 15", "category": "Electronics", "price": 1299.99, "stock": 45, "rating": 4.5, "status": "in_stock"},
            {"id": 2, "name": "Wireless Mouse", "category": "Accessories", "price": 29.99, "stock": 150, "rating": 4.2, "status": "in_stock"},
            {"id": 3, "name": "USB-C Cable", "category": "Accessories", "price": 12.99, "stock": 300, "rating": 4.8, "status": "in_stock"},
            {"id": 4, "name": "Monitor 27\"", "category": "Electronics", "price": 399.99, "stock": 0, "rating": 4.6, "status": "out_of_stock"},
            {"id": 5, "name": "Mechanical Keyboard", "category": "Accessories", "price": 149.99, "stock": 67, "rating": 4.7, "status": "in_stock"},
            {"id": 6, "name": "Webcam HD", "category": "Electronics", "price": 79.99, "stock": 23, "rating": 4.3, "status": "in_stock"},
            {"id": 7, "name": "Desk Lamp", "category": "Furniture", "price": 45.00, "stock": 88, "rating": 4.4, "status": "in_stock"},
            {"id": 8, "name": "Office Chair", "category": "Furniture", "price": 299.99, "stock": 15, "rating": 4.6, "status": "low_stock"},
        ],
        
        # Users/customers
        "users": [
            {"id": 1, "name": "Alice Johnson", "email": "alice@example.com", "role": "admin", "status": "active", "joined": "2024-01-15"},
            {"id": 2, "name": "Bob Smith", "email": "bob@example.com", "role": "user", "status": "active", "joined": "2024-02-20"},
            {"id": 3, "name": "Carol White", "email": "carol@example.com", "role": "user", "status": "inactive", "joined": "2024-03-10"},
            {"id": 4, "name": "David Brown", "email": "david@example.com", "role": "moderator", "status": "active", "joined": "2024-04-05"},
            {"id": 5, "name": "Eve Davis", "email": "eve@example.com", "role": "user", "status": "active", "joined": "2024-05-12"},
        ],
        
        # Sales data
        "sales": [
            {"id": 1, "date": "2024-11-20", "product": "Laptop Pro 15", "quantity": 5, "revenue": 6499.95, "region": "North"},
            {"id": 2, "date": "2024-11-20", "product": "Wireless Mouse", "quantity": 23, "revenue": 689.77, "region": "South"},
            {"id": 3, "date": "2024-11-21", "product": "Monitor 27\"", "quantity": 8, "revenue": 3199.92, "region": "East"},
            {"id": 4, "date": "2024-11-21", "product": "Mechanical Keyboard", "quantity": 12, "revenue": 1799.88, "region": "West"},
            {"id": 5, "date": "2024-11-22", "product": "Office Chair", "quantity": 6, "revenue": 1799.94, "region": "North"},
            {"id": 6, "date": "2024-11-22", "product": "Webcam HD", "quantity": 15, "revenue": 1199.85, "region": "South"},
            {"id": 7, "date": "2024-11-23", "product": "USB-C Cable", "quantity": 45, "revenue": 584.55, "region": "East"},
        ],
        
        # Tasks/projects
        "tasks": [
            {"id": 1, "title": "Update documentation", "assignee": "Alice Johnson", "status": "completed", "priority": "medium", "due": "2024-11-25"},
            {"id": 2, "title": "Fix login bug", "assignee": "Bob Smith", "status": "in_progress", "priority": "high", "due": "2024-11-24"},
            {"id": 3, "title": "Design new homepage", "assignee": "Carol White", "status": "pending", "priority": "low", "due": "2024-11-30"},
            {"id": 4, "title": "API optimization", "assignee": "David Brown", "status": "in_progress", "priority": "high", "due": "2024-11-26"},
            {"id": 5, "title": "Write unit tests", "assignee": "Eve Davis", "status": "pending", "priority": "medium", "due": "2024-11-28"},
            {"id": 6, "title": "Security audit", "assignee": "Alice Johnson", "status": "completed", "priority": "high", "due": "2024-11-23"},
        ],
        
        # Analytics/metrics
        "metrics": [
            {"date": "2024-11-17", "pageviews": 1523, "users": 342, "revenue": 8234.50, "conversions": 45},
            {"date": "2024-11-18", "pageviews": 1678, "users": 389, "revenue": 9156.25, "conversions": 52},
            {"date": "2024-11-19", "pageviews": 1445, "users": 321, "revenue": 7890.00, "conversions": 41},
            {"date": "2024-11-20", "pageviews": 1892, "users": 445, "revenue": 10234.75, "conversions": 58},
            {"date": "2024-11-21", "pageviews": 2103, "users": 498, "revenue": 11567.50, "conversions": 67},
            {"date": "2024-11-22", "pageviews": 1789, "users": 412, "revenue": 9876.25, "conversions": 54},
            {"date": "2024-11-23", "pageviews": 1956, "users": 456, "revenue": 10456.00, "conversions": 61},
        ],
        
        # Orders
        "orders": [
            {"id": 1001, "customer": "Alice Johnson", "items": 3, "total": 449.97, "status": "delivered", "date": "2024-11-20"},
            {"id": 1002, "customer": "Bob Smith", "items": 1, "total": 1299.99, "status": "shipped", "date": "2024-11-21"},
            {"id": 1003, "customer": "Carol White", "items": 5, "total": 234.95, "status": "processing", "date": "2024-11-22"},
            {"id": 1004, "customer": "David Brown", "items": 2, "total": 549.98, "status": "delivered", "date": "2024-11-22"},
            {"id": 1005, "customer": "Eve Davis", "items": 4, "total": 678.96, "status": "pending", "date": "2024-11-23"},
        ],
        
        # Summary stats
        "summary": {
            "total_revenue": 45234.50,
            "total_orders": 234,
            "active_users": 1245,
            "avg_order_value": 193.31,
            "top_product": "Laptop Pro 15",
            "growth_rate": 12.5
        }
    }

    logger.info(f"Returning mock data with keys: {list(mock_data.keys())}")
    logger.info(f"Tasks count: {len(mock_data.get('tasks', []))}")
    return mock_data


@router.put("/{component_id}/feedback")
async def add_feedback(component_id: str, feedback: ComponentFeedback, request: Request):
    tenant_id = get_tenant_id(request)
    user_id = get_user_id(request)
    supabase = get_supabase()

    try:
        supabase.rpc(
            'set_config',
            {'setting': 'app.tenant_id', 'value': tenant_id}
        ).execute()
    except:
        pass

    component_result = supabase.table("components").select("id").eq(
        "id", component_id
    ).eq("tenant_id", tenant_id).execute()

    if not component_result.data:
        raise HTTPException(status_code=404, detail="Component not found")

    supabase.table("component_feedback").insert({
        "component_id": component_id,
        "user_id": user_id,
        "rating": feedback.rating,
        "feedback_text": feedback.feedback_text
    }).execute()

    logger.info(f"Feedback added: component={component_id}, rating={feedback.rating}")

    return {"status": "success"}


@router.post("/{component_id}/render-metrics")
async def receive_render_metrics(component_id: str, request: Request, metrics: dict = None):
    """Receive client-side render timing metrics from iframe"""
    tenant_id = get_tenant_id(request)
    user_id = get_user_id(request)
    
    if metrics and metrics.get("timing"):
        timing_data = metrics.get("timing", {})
        total_time = timing_data.get("total-request-to-render")
        
        log_data = {
            "event": "component_render_metrics",
            "timestamp": datetime.utcnow().isoformat(),
            "component_id": component_id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "render_timing": timing_data
        }
        
        # Log total time prominently if available
        if total_time:
            log_data["total_request_to_render_ms"] = total_time
            logger.info(
                json.dumps({
                    "event": "micro_app_total_time",
                    "timestamp": datetime.utcnow().isoformat(),
                    "component_id": component_id,
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "total_time_ms": total_time,
                    "breakdown": timing_data
                })
            )
        
        logger.info(json.dumps(log_data))
    
    return {"status": "received"}


@router.put("/{component_id}/archive")
async def archive_component(component_id: str, request: Request):
    tenant_id = get_tenant_id(request)
    supabase = get_supabase()

    try:
        supabase.rpc(
            'set_config',
            {'setting': 'app.tenant_id', 'value': tenant_id}
        ).execute()
    except:
        pass

    result = supabase.table("components").update({
        "status": "archived"
    }).eq("id", component_id).eq("tenant_id", tenant_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Component not found")

    return {"status": "archived"}
