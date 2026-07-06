#!/bin/bash
set -euo pipefail

# F1 Prediction System - One-Command Demo Script
# Academic research project demonstration

echo "🏎️  F1 Race Prediction System - Academic Demo"
echo "=============================================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is required but not installed"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q -r requirements.txt

# Check if model exists, if not suggest training
if [ ! -f "model/f1_model.pkl" ]; then
    echo "⚠️  Model not found at model/f1_model.pkl"
    echo "💡 To train the model:"
    echo "   1. Download data: python data/download_data.py"
    echo "   2. Train model: jupyter notebook model/train_model.ipynb"
    echo ""
    echo "🔄 Demo will use statistical fallback predictions"
    echo ""
fi

# Function to open browser on macOS/Linux
open_browser() {
    local url="$1"
    
    # Detect OS and open browser
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        open "$url"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v xdg-open &> /dev/null; then
            xdg-open "$url"
        elif command -v gnome-open &> /dev/null; then
            gnome-open "$url"
        else
            echo "🌐 Open your browser to: $url"
        fi
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        # Windows
        start "$url"
    else
        echo "🌐 Open your browser to: $url"
    fi
}

# Function to run standalone demo
run_standalone_demo() {
    echo "🔮 Running standalone prediction demo..."
    echo ""
    python demo.py
    echo ""
    echo "✅ Standalone demo completed!"
}

# Function to run Flask web demo
run_web_demo() {
    echo "🌐 Starting Flask web application..."
    echo "📍 Server will start at: http://localhost:5000"
    echo "🔄 Press Ctrl+C to stop the server"
    echo ""
    
    # Start Flask in background
    python app.py &
    FLASK_PID=$!
    
    # Wait a moment for server to start
    sleep 3
    
    # Check if server is running
    if curl -s http://localhost:5000/health > /dev/null; then
        echo "✅ Server started successfully!"
        echo "🌐 Opening browser..."
        open_browser "http://localhost:5000"
        
        echo ""
        echo "📋 Available endpoints:"
        echo "  🏠 Main App: http://localhost:5000"
        echo "  📊 Health Check: http://localhost:5000/health"
        echo "  🔮 API Predict: http://localhost:5000/api/predict"
        echo "  📈 History: http://localhost:5000/api/history"
        echo ""
        echo "🛑 Press Enter to stop the demo..."
        read -r
        
        # Kill Flask server
        kill $FLASK_PID 2>/dev/null
        echo "🛑 Server stopped"
    else
        echo "❌ Failed to start server"
        kill $FLASK_PID 2>/dev/null
        exit 1
    fi
}

# Main menu
echo "🎯 Choose demo type:"
echo "1) 📊 Standalone Demo (command line table output)"
echo "2) 🌐 Web Demo (Flask server + browser)"
echo "3) 📚 Both demos"
echo ""
read -p "Enter choice (1-3): " choice

case $choice in
    1)
        run_standalone_demo
        ;;
    2)
        run_web_demo
        ;;
    3)
        run_standalone_demo
        echo ""
        echo "🔄 Now starting web demo..."
        echo "⏱️  Waiting 2 seconds..."
        sleep 2
        run_web_demo
        ;;
    *)
        echo "❌ Invalid choice. Running standalone demo..."
        run_standalone_demo
        ;;
esac

echo ""
echo "📋 Next Steps for Research:"
echo "1. 📊 Analyze results in: analysis/research_analysis.ipynb"
echo "2. 📖 Read methodology: README.md"
echo "3. 🔬 Train custom model: model/train_model.ipynb"
echo "4. 📈 Download more data: python data/download_data.py"
echo ""
echo "🎓 Academic Research Project Complete!"
echo "📄 Citation: F1 Race Predictor - XGBoost Approach (2024)"