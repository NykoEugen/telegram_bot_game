#!/usr/bin/env python3
"""
Simple test script to verify bot setup and configuration.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to Python path
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

async def test_database():
    """Test database connection and operations."""
    print("Testing database connection...")
    
    try:
        from app.database import (
            init_db,
            AsyncSessionLocal,
            create_user,
            get_user_by_telegram_id,
            User,
        )
        
        # Initialize database
        await init_db()
        print("✅ Database initialized successfully")
        
        # Test database operations
        async with AsyncSessionLocal() as session:
            # Test user creation
            existing_user = await get_user_by_telegram_id(session, 12345)
            if existing_user:
                print("ℹ️ Test user already existed; removing for a clean run...")
                await session.delete(existing_user)
                await session.commit()

            test_user = await create_user(
                session=session,
                user_id=12345,
                username="test_user",
                first_name="Test",
                last_name="User",
                is_bot=False,
                language_code="en"
            )
            print(f"✅ Test user created: {test_user}")
            
            # Test user retrieval
            retrieved_user = await get_user_by_telegram_id(session, 12345)
            if retrieved_user:
                print(f"✅ Test user retrieved: {retrieved_user}")
            else:
                print("❌ Failed to retrieve test user")
                
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False
    
    return True


async def test_config():
    """Test configuration loading."""
    print("Testing configuration...")
    
    try:
        # Set test environment variables
        os.environ["BOT_TOKEN"] = "test_token"
        os.environ["WEBHOOK_DOMAIN"] = "test.ngrok.io"
        
        from app.config import Config
        
        print(f"✅ BOT_TOKEN: {Config.BOT_TOKEN}")
        print(f"✅ WEBHOOK_HOST: {Config.WEBHOOK_HOST}")
        print(f"✅ WEBHOOK_PORT: {Config.WEBHOOK_PORT}")
        print(f"✅ WEBHOOK_DOMAIN: {Config.WEBHOOK_DOMAIN}")
        print(f"✅ DATABASE_URL: {Config.DATABASE_URL}")
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False
    
    return True


def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    modules_to_test = [
        "aiogram",
        "aiohttp", 
        "sqlalchemy",
        "aiosqlite"
    ]
    
    failed_imports = []
    
    for module in modules_to_test:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError as e:
            print(f"❌ {module}: {e}")
            failed_imports.append(module)
    
    if failed_imports:
        print(f"\n❌ Failed to import: {', '.join(failed_imports)}")
        print("Please install missing dependencies with: pip install -r requirements.txt")
        return False
    
    return True


async def main():
    """Run all tests."""
    print("🧪 Running bot setup tests...\n")
    
    tests = [
        ("Import Test", test_imports),
        ("Configuration Test", test_config),
        ("Database Test", test_database)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Your bot setup is ready.")
        print("\nNext steps:")
        print("1. Copy env.template to .env")
        print("2. Update .env with your bot token and ngrok domain")
        print("3. Start ngrok: ngrok http 8080")
        print("4. Run the bot: python start.py")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please fix the issues above.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
