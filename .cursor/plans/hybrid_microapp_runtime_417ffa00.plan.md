---
name: Hybrid Microapp Runtime
overview: Embed Appsmith CE inside Spark as the primary microapp builder/runtime, while keeping Spark’s existing LLM-generated sandboxed microapps as a fallback; unify both in the existing Components panel via a single iframe-based microapp surface with clear metadata and routing.
todos:
  - id: compose-appsmith
    content: Add Appsmith CE service (and any required deps) + reverse proxy routing `/appsmith/*` in `docker-compose.yml`.
    status: pending
  - id: schema-microapp-kind
    content: Add Supabase migration to extend `chat_messages` with `microapp_kind` + `appsmith_path` (backwards compatible with `component_id`).
    status: pending
  - id: backend-microapp-response
    content: Update backend models and `chat.py` to persist/return Appsmith microapp references in addition to `component_id`.
    status: pending
    dependencies:
      - schema-microapp-kind
  - id: frontend-microapp-iframe
    content: Implement unified `MicroappIframe` and update `ComponentsView` to render either Spark component iframe or Appsmith iframe in the same panel.
    status: pending
    dependencies:
      - backend-microapp-response
  - id: llm-hybrid-routing
    content: Extend `LLMService` prompt/response parsing to allow `type=appsmith_app` using a curated template/path list; keep `type=component` as fallback.
    status: pending
    dependencies:
      - backend-microapp-response
---

# Hybrid Appsmith + Spark Microapps Plan

## Goals

- **Primary**: Embed **Appsmith OSS (Apache-2.0)** inside Spark as a full-featured microapp builder/runtime (rich widgets, rich text, reactive bindings).
- **Fallback**: Keep Spark’s existing **LLM-generated microapps** (currently SolidJS compiled and rendered in a sandboxed iframe) for cases where Appsmith isn’t enough or is too slow/verbose.
- **UX**: A **single unified “microapp panel”** that can render either type.

## Key repo facts (what we’ll leverage)

- Spark already renders generated microapps in an iframe at `/api/components/{component_id}/iframe` via [`backend/app/routers/components.py`](/Users/kanwari/git/spark/backend/app/routers/components.py) and [`frontend/src/components/ComponentIframe.tsx`](/Users/kanwari/git/spark/frontend/src/components/ComponentIframe.tsx).
- The chat pipeline already persists `chat_messages.component_id` and returns `ChatResponse(type='component', component_id=...)` via [`backend/app/routers/chat.py`](/Users/kanwari/git/spark/backend/app/routers/chat.py) and [`backend/app/services/llm.py`](/Users/kanwari/git/spark/backend/app/services/llm.py).

## Architecture

```mermaid
flowchart LR
  user[User] --> sparkUI[SparkUI]
  sparkUI --> microappPanel[UnifiedMicroappPanel]

  microappPanel -->|SparkComponent| sparkIframe[/api/components/{id}/iframe/]
  microappPanel -->|AppsmithApp| appsmithIframe[/appsmith/{path}/]

  sparkIframe --> sparkBackend[SparkBackend]
  appsmithIframe --> appsmith[AppsmithCE]

  sparkBackend --> supabase[(Supabase)]
  appsmith --> appsmithDB[(AppsmithDB)]
```

## Data model changes (minimal + backwards compatible)

- Extend `chat_messages` to support **either** a Spark component **or** an Appsmith reference.
  - Add columns (new Supabase migration):
    - `microapp_kind text` (e.g. `spark_component | appsmith_app`)
    - `appsmith_path text` (e.g. `/app/my-app/page-1` or an app/page identifier we can resolve)
    - Keep existing `component_id` for current Spark components.
- Update backend Pydantic models in [`backend/app/models/__init__.py`](/Users/kanwari/git/spark/backend/app/models/__init__.py):
  - `ChatResponse`: allow `type: text | component | appsmith_app` (or normalize to `type: microapp` + `microapp_kind`).
- Update frontend types in [`frontend/src/types/index.ts`](/Users/kanwari/git/spark/frontend/src/types/index.ts) similarly.

## Appsmith embedding approach (practical MVP)

- Run Appsmith CE alongside Spark via Docker Compose (new service).
- Expose Appsmith behind the same origin under `/appsmith/*` using a reverse proxy container (recommended for cookies/SSO later and to avoid CORS headaches).
  - **MVP**: proxy only; users authenticate to Appsmith separately.
  - **Next**: add SSO (OIDC/SAML) so Spark and Appsmith share identity.

## Unified microapp panel implementation

- Generalize the current iframe component:
  - Create `MicroappIframe` in [`frontend/src/components/`](/Users/kanwari/git/spark/frontend/src/components/) that renders either:
    - Spark iframe: `/api/components/{id}/iframe` (existing behavior)
    - Appsmith iframe: `/appsmith/...` (new)
- Update [`frontend/src/components/ComponentsView.tsx`](/Users/kanwari/git/spark/frontend/src/components/ComponentsView.tsx) to become a unified “microapps view”:
  - Display both Spark components and Appsmith microapps referenced in the chat session.

## Microapp edit mode (chat against the microapp)

- Add a **side-channel chat** that is explicitly **scoped to the currently active microapp** (not the whole session).
  - UX: when a microapp is open in the unified panel, show an “Edit this microapp” chat drawer.
  - The user can ask: “Add a filter”, “Change the chart to bar”, “Make it a 2-column layout”, etc.
- The LLM should **modify the existing microapp** rather than generating a new one from scratch:
  - **Spark microapps**: use the existing `components.solidjs_code` as input context and ask the LLM to return an updated version (or a patch) that preserves intent.
  - **Appsmith microapps (MVP)**: treat edits as **navigation to an existing template/path** or guided steps; later we can add programmatic updates if we adopt Appsmith APIs.
- Re-render strategy (the “fast iteration” loop):
  - Apply the same **fast shell + progress stepper + early iframe load** UX.
  - When a new compiled artifact is ready, **re-render the iframe** rather than creating a brand-new microapp entry.
    - simplest: bump a `renderNonce` and set iframe `src` to `.../iframe?rev=<nonce>` to force reload
    - better: add a `component_version` and reload on version change
  - Keep a stable “microapp identity” while versions change.
- Data/traceability:
  - Persist `edit_parent_component_id` (or `microapp_root_id`) so we can show edit history and enable rollback.
  - Keep edit chats separate from the main chat thread (so context stays tight and controllable).

## LLM behavior (hybrid decision)

- Update [`backend/app/services/llm.py`](/Users/kanwari/git/spark/backend/app/services/llm.py) system prompt + parsing to support:
  - `type: component` (existing)
  - `type: appsmith_app` when the request is better served by Appsmith widgets/workflows (forms, CRUD admin, multi-page apps, rich text docs)
  - For `appsmith_app`, return a **template selection** or **path** (initially from a curated list) rather than trying to fully programmatically author Appsmith JSON.

## Security model (sandboxed JS)

- Keep Spark microapps in iframe sandbox (already present) and tighten capabilities over time:
  - **Near-term**: standardize a `postMessage` capability API (e.g. `spark.fetchData`, `spark.navigate`, `spark.emitEvent`) so generated code doesn’t need wide privileges.
  - **Later**: remove `allow-same-origin` for Spark microapps and move API access to message-passing + short-lived tokens.
- Appsmith iframe remains sandboxed but will likely need `allow-same-origin`/`allow-forms` for normal operation.

## Files we’ll likely touch

- Frontend:
  - [`frontend/src/components/ComponentIframe.tsx`](/Users/kanwari/git/spark/frontend/src/components/ComponentIframe.tsx) (factor into `MicroappIframe`)
  - [`frontend/src/components/ComponentsView.tsx`](/Users/kanwari/git/spark/frontend/src/components/ComponentsView.tsx) (support Appsmith microapps)
  - [`frontend/src/types/index.ts`](/Users/kanwari/git/spark/frontend/src/types/index.ts)
  - [`frontend/src/services/api.ts`](/Users/kanwari/git/spark/frontend/src/services/api.ts) (if we add endpoints to list microapps)
- Backend:
  - [`backend/app/models/__init__.py`](/Users/kanwari/git/spark/backend/app/models/__init__.py)
  - [`backend/app/routers/chat.py`](/Users/kanwari/git/spark/backend/app/routers/chat.py)
  - [`backend/app/services/llm.py`](/Users/kanwari/git/spark/backend/app/services/llm.py)
  - Add `backend/app/routers/appsmith_proxy.py` (or proxy at infra layer only)
- Infra:
  - [`docker-compose.yml`](/Users/kanwari/git/spark/docker-compose.yml) (add Appsmith + reverse proxy)
  - New Supabase migration under [`supabase/migrations/`](/Users/kanwari/git/spark/supabase/migrations/)

## Milestones

1. **Embed Appsmith** in Spark (docker-compose + reverse proxy + iframe route).
2. **Unified microapp panel** that can show Spark component iframes and Appsmith iframes.
3. **Chat + DB wiring**: store/retrieve `microapp_kind` and `appsmith_path` in `chat_messages`.
4. **Microapp edit mode**: side-channel chat scoped to a microapp + re-render iframe on edits (no incremental streaming yet).
5. **LLM hybrid output**: enable `appsmith_app` responses using curated template/path selection.
6. **Security hardening**: capability-based API for Spark microapps + reduce iframe permissions.