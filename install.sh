#!/bin/bash

# Solana Grid Trading Bot Installation Script
# ===========================================

set -e  # Exit on any error

echo "🚀 Solana Grid Trading Bot Installation"
echo "======================================"

# Check Python version
echo "🔍 Checking Python version..."
python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
echo "Found Python $python_version"

# Check if Python 3.8+ is available
if command -v python3.11 &> /dev/null; then
    echo "✅ Python 3.11+ found, using it for better compatibility"
    PYTHON_CMD="python3.11"
elif command -v python3.10 &> /dev/null; then
    echo "✅ Python 3.10 found, using it for better compatibility"
    PYTHON_CMD="python3.10"
elif command -v python3.9 &> /dev/null; then
    echo "✅ Python 3.9 found, using it for better compatibility"
    PYTHON_CMD="python3.9"
elif command -v python3.8 &> /dev/null; then
    echo "✅ Python 3.8 found, using it for better compatibility"
    PYTHON_CMD="python3.8"
else
    echo "⚠️  Using system Python (may have compatibility issues)"
    PYTHON_CMD="python3"
fi

# Create virtual environment
echo "🔧 Creating virtual environment..."
if [ -d "venv" ]; then
    echo "✅ Virtual environment already exists"
else
    $PYTHON_CMD -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install core dependencies
echo "📦 Installing core dependencies..."
pip install -r requirements.txt

# Try to install optional dependencies
echo "📦 Installing optional dependencies..."
if pip install psutil==5.9.6 2>/dev/null; then
    echo "✅ Optional dependencies installed"
else
    echo "⚠️  Optional dependencies not installed (not required)"
fi

# Create directories
echo "📁 Creating directories..."
mkdir -p logs data backups

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️  Creating .env file..."
    cp env.example .env
    echo "✅ .env file created from template"
    echo "📝 Please edit .env file with your API credentials"
else
    echo "✅ .env file already exists"
fi

# Run tests
echo "🧪 Running tests..."
if python test_bot.py > /dev/null 2>&1; then
    echo "✅ All tests passed"
else
    echo "⚠️  Some tests failed (may need .env configuration)"
fi

echo ""
echo "🎉 Installation completed successfully!"
echo ""
echo "📋 Next Steps:"
echo "1. Edit .env file with your API credentials:"
echo "   nano .env"
echo ""
echo "2. Test the bot in dry-run mode:"
echo "   source venv/bin/activate"
echo "   python main.py --dry-run"
echo ""
echo "3. Start live trading:"
echo "   python main.py"
echo ""
echo "📚 Documentation: README.md"
echo "🆘 Support: Check logs/ directory for detailed logs" 