import subprocess
import tempfile
import os
import time
import hashlib
import logging
import json
from typing import Optional
from app.models import CompilationResult
from app.config import settings
from app.database import get_redis

logger = logging.getLogger(__name__)


class ComponentCompiler:
    # Shared compilation workspace
    _workspace_dir = None
    _workspace_initialized = False

    def __init__(self):
        self.esbuild_config = {
            "bundle": True,
            "minify": True,
            "format": "iife",
            "target": "es2020",
            "jsx": "automatic",
            "jsxImportSource": "solid-js",
            "treeShaking": True,
            # External dependencies loaded via CDN in iframe
            "external": ["solid-js", "solid-js/web", "solid-js/store", "apexcharts"]
        }
        self._ensure_workspace()
    
    def _ensure_workspace(self):
        """Create a persistent compilation workspace with node_modules"""
        if ComponentCompiler._workspace_initialized:
            return
        
        # Use /tmp/spark-compiler as workspace
        ComponentCompiler._workspace_dir = "/tmp/spark-compiler"
        os.makedirs(ComponentCompiler._workspace_dir, exist_ok=True)
        
        package_json = os.path.join(ComponentCompiler._workspace_dir, "package.json")
        if not os.path.exists(package_json):
            dependencies = {
                "solid-js": "^1.8.7",
                "babel-preset-solid": "^1.8.16",
                "@babel/core": "^7.24.0",
                "@babel/cli": "^7.24.0",
                "apexcharts": "^3.54.1"
            }
            with open(package_json, "w") as f:
                json.dump({"dependencies": dependencies}, f)
            
            # Install dependencies once
            logger.info("Installing solid-js and babel for compilation workspace...")
            try:
                result = subprocess.run(
                    ["npm", "install", "--silent", "--no-audit", "--no-fund"],
                    cwd=ComponentCompiler._workspace_dir,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if result.returncode == 0:
                    logger.info("Compilation workspace initialized")
                    ComponentCompiler._workspace_initialized = True
                else:
                    logger.error(f"Failed to initialize workspace: {result.stderr}")
            except Exception as e:
                logger.error(f"Workspace initialization error: {e}")

    async def compile(self, code: str, code_hash: str) -> CompilationResult:
        redis_client = await get_redis()
        cache_key = f"compiled:{code_hash}"

        if redis_client:
            try:
                cached = await redis_client.get(cache_key)
                if cached:
                    logger.info(f"Cache hit for code_hash={code_hash}")
                    bundle_size = len(cached.encode('utf-8'))
                    return CompilationResult(
                        success=True,
                        bundle=cached,
                        bundle_size=bundle_size,
                        compile_time_ms=0
                    )
            except Exception as e:
                logger.warning(f"Cache read failed: {e}")

        start_time = time.time()

        try:
            bundle = await self._run_esbuild(code)
            compile_time_ms = int((time.time() - start_time) * 1000)
            bundle_size = len(bundle.encode('utf-8'))

            if bundle_size > settings.max_bundle_size_bytes:
                return CompilationResult(
                    success=False,
                    error=f"Compiled bundle size ({bundle_size} bytes) exceeds maximum ({settings.max_bundle_size_bytes} bytes)"
                )

            if redis_client:
                try:
                    await redis_client.setex(
                        cache_key,
                        settings.cache_ttl_seconds,
                        bundle
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
                compile_time_ms=compile_time_ms
            )

        except Exception as e:
            compile_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Compilation failed: {str(e)}")
            return CompilationResult(
                success=False,
                error=str(e),
                compile_time_ms=compile_time_ms
            )

    async def _run_esbuild(self, code: str) -> str:
        # Write component to workspace
        input_file = os.path.join(ComponentCompiler._workspace_dir, "component.jsx")
        babel_output = os.path.join(ComponentCompiler._workspace_dir, "component.babel.js")
        output_file = os.path.join(ComponentCompiler._workspace_dir, "component.js")
        babel_config = os.path.join(ComponentCompiler._workspace_dir, ".babelrc")

        with open(input_file, "w") as f:
            f.write(code)
        
        # Create babel config for solid-js
        if not os.path.exists(babel_config):
            with open(babel_config, "w") as f:
                f.write('{"presets": ["babel-preset-solid"]}')
        
        # Step 1: Transform JSX with babel-preset-solid
        babel_cmd = [
            "npx", "babel",
            input_file,
            "--out-file", babel_output,
            "--config-file", babel_config
        ]
        
        babel_result = subprocess.run(
            babel_cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=ComponentCompiler._workspace_dir
        )
        
        if babel_result.returncode != 0:
            raise Exception(f"Babel transform failed: {babel_result.stderr}")
        
        # Step 2: Bundle with esbuild (with optimizations)
        # Use ESM format with external dependencies (loaded via importmap in iframe)
        # This keeps bundles small while leveraging the browser's native module system
        cmd = [
            "npx", "esbuild",
            babel_output,
            "--bundle",
            "--minify",
            "--format=esm",
            "--target=es2020",
            "--tree-shaking=true",
            # External dependencies (loaded via CDN in iframe importmap)
            "--external:solid-js",
            "--external:solid-js/web",
            "--external:solid-js/store",
            "--external:apexcharts",
            f"--outfile={output_file}"
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=settings.compilation_timeout_seconds,
                cwd=ComponentCompiler._workspace_dir
            )

            if result.returncode != 0:
                raise Exception(f"esbuild failed: {result.stderr}")

            with open(output_file, "r") as f:
                bundle = f.read()
            
            # Clean up temp files
            try:
                os.remove(input_file)
                os.remove(babel_output)
                os.remove(output_file)
            except:
                pass
            
            return bundle

        except subprocess.TimeoutExpired:
            raise Exception("Compilation timeout exceeded")
        except FileNotFoundError:
            raise Exception("esbuild not found. Ensure Node.js and esbuild are installed")

    @staticmethod
    def compute_hash(code: str) -> str:
        return hashlib.sha256(code.encode('utf-8')).hexdigest()
