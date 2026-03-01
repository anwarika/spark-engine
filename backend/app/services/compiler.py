import subprocess
import tempfile
import os
import time
import hashlib
import logging
import json
from typing import Optional
from pathlib import Path

from app.models import CompilationResult
from app.config import settings
from app.database import get_redis

logger = logging.getLogger(__name__)

# Path to the Node.js React compiler script
COMPILER_DIR = Path(__file__).resolve().parents[2] / "compiler"
ESBUILD_SCRIPT = COMPILER_DIR / "esbuild-build.mjs"


class ComponentCompiler:
    # Shared compilation workspace
    _workspace_dir = None
    _workspace_initialized = False

    def __init__(self):
        self._ensure_workspace()

    def _ensure_workspace(self):
        """Ensure compiler dependencies are installed."""
        if ComponentCompiler._workspace_initialized:
            return

        if not ESBUILD_SCRIPT.exists():
            raise RuntimeError(f"Compiler script not found: {ESBUILD_SCRIPT}")

        package_json = COMPILER_DIR / "package.json"
        if package_json.exists():
            logger.info("Installing React compiler dependencies...")
            try:
                result = subprocess.run(
                    ["npm", "install", "--silent", "--no-audit", "--no-fund"],
                    cwd=COMPILER_DIR,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if result.returncode == 0:
                    logger.info("Compiler workspace initialized")
                    ComponentCompiler._workspace_initialized = True
                else:
                    logger.error(f"Compiler npm install failed: {result.stderr}")
            except Exception as e:
                logger.error(f"Compiler setup error: {e}")
        else:
            ComponentCompiler._workspace_initialized = True

    async def compile(self, code: str, code_hash: str) -> CompilationResult:
        redis_client = await get_redis()
        cache_key = f"compiled:react:{code_hash}"

        if redis_client:
            try:
                cached = await redis_client.get(cache_key)
                if cached:
                    logger.info(f"Cache hit for code_hash={code_hash}")
                    bundle_size = len(cached.encode("utf-8"))
                    return CompilationResult(
                        success=True,
                        bundle=cached,
                        bundle_size=bundle_size,
                        compile_time_ms=0,
                    )
            except Exception as e:
                logger.warning(f"Cache read failed: {e}")

        start_time = time.time()

        try:
            bundle = await self._run_esbuild(code)
            compile_time_ms = int((time.time() - start_time) * 1000)
            bundle_size = len(bundle.encode("utf-8"))

            if bundle_size > settings.max_bundle_size_bytes:
                return CompilationResult(
                    success=False,
                    error=f"Compiled bundle size ({bundle_size} bytes) exceeds maximum ({settings.max_bundle_size_bytes} bytes)",
                )

            if redis_client:
                try:
                    await redis_client.setex(
                        cache_key,
                        settings.cache_ttl_seconds,
                        bundle,
                    )
                except Exception as e:
                    logger.warning(f"Cache write failed: {e}")

            logger.info(
                f"Compilation successful: code_hash={code_hash}, "
                f"size={bundle_size}, time={compile_time_ms}ms"
            )

            return CompilationResult(
                success=True,
                bundle=bundle,
                bundle_size=bundle_size,
                compile_time_ms=compile_time_ms,
            )

        except Exception as e:
            compile_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Compilation failed: {str(e)}")
            return CompilationResult(
                success=False,
                error=str(e),
                compile_time_ms=compile_time_ms,
            )

    async def _run_esbuild(self, code: str) -> str:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".tsx",
            delete=False,
        ) as f:
            f.write(code)
            input_path = f.name

        try:
            result = subprocess.run(
                ["node", str(ESBUILD_SCRIPT), input_path],
                capture_output=True,
                text=True,
                timeout=settings.compilation_timeout_seconds,
                cwd=COMPILER_DIR,
            )

            if result.returncode != 0:
                raise Exception(f"esbuild failed: {result.stderr}")

            return result.stdout
        finally:
            try:
                os.unlink(input_path)
            except OSError:
                pass

    @staticmethod
    def compute_hash(code: str) -> str:
        return hashlib.sha256(code.encode("utf-8")).hexdigest()
