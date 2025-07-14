#!/usr/bin/env python3
"""
Setup script for Solana Grid Trading Bot
========================================

This script helps users set up the trading bot with proper configuration
and validation.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def print_banner():
    """Print setup banner."""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║              SOLANA GRID TRADING BOT SETUP                   ║
║                                                              ║
║  🚀 Maximum Profitability & Security                        ║
║  🔒 Advanced Risk Management                                ║
║  📊 Real-time Performance Tracking                          ║
║  🛡️  Enterprise-grade Security                              ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)

def check_python_version():
    """Check if Python version is compatible."""
    print("🔍 Checking Python version...")
    
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"   Current version: {sys.version}")
        return False
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    return True

def create_virtual_environment():
    """Create virtual environment if it doesn't exist."""
    print("🔧 Setting up virtual environment...")
    
    venv_path = Path("venv")
    if venv_path.exists():
        print("✅ Virtual environment already exists")
        return True
    
    try:
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
        print("✅ Virtual environment created successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create virtual environment: {e}")
        return False

def install_dependencies():
    """Install required dependencies."""
    print("📦 Installing dependencies...")
    
    # Determine the correct pip path
    if os.name == 'nt':  # Windows
        pip_path = "venv\\Scripts\\pip"
    else:  # Unix/Linux/macOS
        pip_path = "venv/bin/pip"
    
    try:
        # First try to upgrade pip
        subprocess.run([pip_path, "install", "--upgrade", "pip"], check=True)
        print("✅ Pip upgraded successfully")
        
        # Install core dependencies
        subprocess.run([pip_path, "install", "-r", "requirements.txt"], check=True)
        print("✅ Core dependencies installed successfully")
        
        # Try to install optional dependencies if available
        try:
            subprocess.run([pip_path, "install", "psutil==5.9.6"], check=True)
            print("✅ Optional dependencies installed successfully")
        except subprocess.CalledProcessError:
            print("⚠️  Optional dependencies not installed (not required)")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        print("💡 Try installing manually: pip install -r requirements.txt")
        return False

def create_env_file():
    """Create .env file from template."""
    print("⚙️  Setting up configuration...")
    
    env_file = Path(".env")
    env_example = Path("env.example")
    
    if env_file.exists():
        print("✅ .env file already exists")
        return True
    
    if not env_example.exists():
        print("❌ env.example file not found")
        return False
    
    try:
        shutil.copy(env_example, env_file)
        print("✅ .env file created from template")
        print("📝 Please edit .env file with your API credentials")
        return True
    except Exception as e:
        print(f"❌ Failed to create .env file: {e}")
        return False

def create_directories():
    """Create necessary directories."""
    print("📁 Creating directories...")
    
    directories = ["logs", "data", "backups"]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    print("✅ Directories created successfully")

def run_tests():
    """Run test suite to validate installation."""
    print("🧪 Running tests...")
    
    # Determine the correct python path
    if os.name == 'nt':  # Windows
        python_path = "venv\\Scripts\\python"
    else:  # Unix/Linux/macOS
        python_path = "venv/bin/python"
    
    try:
        result = subprocess.run([python_path, "test_bot.py"], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ All tests passed")
            return True
        else:
            print("❌ Some tests failed")
            print("Test output:")
            print(result.stdout)
            print("Test errors:")
            print(result.stderr)
            return False
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to run tests: {e}")
        return False

def display_next_steps():
    """Display next steps for the user."""
    print("\n" + "="*60)
    print("🎉 SETUP COMPLETED SUCCESSFULLY!")
    print("="*60)
    
    print("\n📋 Next Steps:")
    print("1. Edit .env file with your API credentials:")
    print("   nano .env")
    print("   # or")
    print("   code .env")
    
    print("\n2. Test the bot in dry-run mode:")
    print("   source venv/bin/activate  # On Windows: venv\\Scripts\\activate")
    print("   python main.py --dry-run")
    
    print("\n3. Start live trading:")
    print("   python main.py")
    
    print("\n📚 Documentation:")
    print("   - README.md: Complete documentation")
    print("   - env.example: Configuration options")
    print("   - test_bot.py: Run tests anytime")
    
    print("\n⚠️  Important:")
    print("   - Start with small amounts ($100-$200)")
    print("   - Monitor performance closely")
    print("   - Never risk more than you can afford to lose")
    
    print("\n🆘 Support:")
    print("   - Check logs/ directory for detailed logs")
    print("   - Run tests: python test_bot.py")
    print("   - Debug mode: python main.py --log-level DEBUG")

def main():
    """Main setup function."""
    print_banner()
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Create virtual environment
    if not create_virtual_environment():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    # Create .env file
    if not create_env_file():
        sys.exit(1)
    
    # Run tests
    if not run_tests():
        print("⚠️  Tests failed, but setup can continue")
        print("   You may need to configure your .env file first")
    
    # Display next steps
    display_next_steps()

if __name__ == "__main__":
    main() 