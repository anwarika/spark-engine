#!/usr/bin/env python3
"""
Pre-compile built-in component templates at deployment time.
This enables instant component rendering by skipping compilation entirely.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.component_library.templates import COMPONENT_TEMPLATES
from app.services.compiler import ComponentCompiler
from app.services.template_engine import TemplateEngine
from app.database import get_redis
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def precompile_all_templates():
    """Pre-compile all built-in templates and store in Redis."""
    compiler = ComponentCompiler()
    template_engine = TemplateEngine()
    redis = await get_redis()
    
    if not redis:
        logger.error("Redis not available. Cannot pre-compile templates.")
        return False
    
    logger.info(f"Pre-compiling {len(COMPONENT_TEMPLATES)} templates...")
    
    compiled_count = 0
    failed_count = 0
    
    for template_name, template in COMPONENT_TEMPLATES.items():
        logger.info(f"Compiling template: {template_name}")
        
        # For each template, create filled versions for each profile
        profiles = ["ecommerce", "saas", "marketing", "finance", "sales"]
        
        for profile in profiles:
            try:
                # Fill template with profile-specific defaults
                filled_code = template_engine.fill_template(
                    template,
                    f"Show me {template.category} for {profile}",
                    {}
                )
                
                # Compute hash for the filled template
                code_hash = ComponentCompiler.compute_hash(filled_code)
                
                # Compile
                result = await compiler.compile(filled_code, code_hash)
                
                if result.success:
                    # Store in Redis with long TTL (7 days)
                    cache_key = f"precompiled:{template_name}:{profile}"
                    await redis.setex(cache_key, 604800, result.bundle)
                    
                    logger.info(
                        f"✓ Pre-compiled {template_name}:{profile} "
                        f"(size: {result.bundle_size} bytes, time: {result.compile_time_ms}ms)"
                    )
                    compiled_count += 1
                else:
                    logger.error(f"✗ Failed to compile {template_name}:{profile}: {result.error}")
                    failed_count += 1
                    
            except Exception as e:
                logger.error(f"✗ Error compiling {template_name}:{profile}: {e}")
                failed_count += 1
    
    logger.info(f"\nPre-compilation complete:")
    logger.info(f"  ✓ Compiled: {compiled_count}")
    logger.info(f"  ✗ Failed: {failed_count}")
    logger.info(f"  Total templates: {len(COMPONENT_TEMPLATES)}")
    logger.info(f"  Total variants: {compiled_count + failed_count}")
    
    return failed_count == 0


async def verify_precompiled():
    """Verify that pre-compiled templates are available in Redis."""
    redis = await get_redis()
    
    if not redis:
        logger.error("Redis not available.")
        return False
    
    logger.info("\nVerifying pre-compiled templates...")
    
    found_count = 0
    missing_count = 0
    
    for template_name in COMPONENT_TEMPLATES.keys():
        profiles = ["ecommerce", "saas", "marketing", "finance", "sales"]
        for profile in profiles:
            cache_key = f"precompiled:{template_name}:{profile}"
            exists = await redis.exists(cache_key)
            if exists:
                found_count += 1
                logger.info(f"✓ Found: {cache_key}")
            else:
                missing_count += 1
                logger.warning(f"✗ Missing: {cache_key}")
    
    logger.info(f"\nVerification complete:")
    logger.info(f"  ✓ Found: {found_count}")
    logger.info(f"  ✗ Missing: {missing_count}")
    
    return missing_count == 0


async def clear_precompiled():
    """Clear all pre-compiled templates from Redis."""
    redis = await get_redis()
    
    if not redis:
        logger.error("Redis not available.")
        return False
    
    logger.info("Clearing pre-compiled templates...")
    
    cursor = 0
    deleted = 0
    
    while True:
        cursor, keys = await redis.scan(cursor, match="precompiled:*", count=100)
        if keys:
            deleted += await redis.delete(*keys)
        if cursor == 0:
            break
    
    logger.info(f"Cleared {deleted} pre-compiled templates from Redis")
    return True


async def main():
    """Main entry point."""
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "verify":
            success = await verify_precompiled()
            sys.exit(0 if success else 1)
        elif command == "clear":
            await clear_precompiled()
            sys.exit(0)
        elif command == "compile":
            success = await precompile_all_templates()
            sys.exit(0 if success else 1)
        else:
            print(f"Unknown command: {command}")
            print("Usage: precompile_templates.py [compile|verify|clear]")
            sys.exit(1)
    else:
        # Default: compile
        success = await precompile_all_templates()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

