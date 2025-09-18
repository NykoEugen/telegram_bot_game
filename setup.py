#!/usr/bin/env python3
"""
Setup script for the Telegram bot project.
This script helps with initial configuration and dependency installation.
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(command, description):
    """Run a command and handle errors."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        if e.stdout:
            print(f"Output: {e.stdout}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return False


def setup_environment():
    """Set up the environment file."""
    env_file = Path(".env")
    template_file = Path("env.template")
    
    if env_file.exists():
        print("✅ .env file already exists")
        return True
    
    if not template_file.exists():
        print("❌ env.template file not found")
        return False
    
    print("📝 Creating .env file from template...")
    
    # Copy template to .env
    with open(template_file, 'r') as template:
        content = template.read()
    
    with open(env_file, 'w') as env:
        env.write(content)
    
    print("✅ .env file created")
    print("⚠️  Please edit .env file with your actual configuration values")
    return True


def install_dependencies():
    """Install Python dependencies."""
    if not Path("requirements.txt").exists():
        print("❌ requirements.txt not found")
        return False
    
    # Check if we're in a virtual environment
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  Warning: You don't appear to be in a virtual environment")
        print("   Consider creating one with: python -m venv venv")
    
    return run_command(
        f"{sys.executable} -m pip install -r requirements.txt",
        "Installing Python dependencies"
    )


def test_setup():
    """Run the test script to verify setup."""
    if not Path("test_bot.py").exists():
        print("❌ test_bot.py not found")
        return False
    
    return run_command(
        f"{sys.executable} test_bot.py",
        "Running setup tests"
    )


def main():
    """Main setup function."""
    print("🚀 Telegram Bot Setup Script")
    print("=" * 40)
    
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    print(f"📁 Working directory: {script_dir}")
    
    steps = [
        ("Setting up environment file", setup_environment),
        ("Installing dependencies", install_dependencies),
        ("Running tests", test_setup)
    ]
    
    success_count = 0
    total_steps = len(steps)
    
    for description, func in steps:
        print(f"\n--- {description} ---")
        if func():
            success_count += 1
        else:
            print(f"❌ Step failed: {description}")
            break
    
    print("\n" + "=" * 40)
    print("SETUP SUMMARY")
    print("=" * 40)
    
    if success_count == total_steps:
        print("🎉 Setup completed successfully!")
        print("\nNext steps:")
        print("1. Edit .env file with your bot token and ngrok domain")
        print("2. Install and start ngrok: ngrok http 8080")
        print("3. Update WEBHOOK_DOMAIN in .env with your ngrok URL")
        print("4. Run the bot: python start.py")
    else:
        print(f"⚠️  Setup incomplete ({success_count}/{total_steps} steps completed)")
        print("Please resolve the errors above and run setup again")
        sys.exit(1)


if __name__ == "__main__":
    main()
