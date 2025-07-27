#!/bin/bash

# F1 Prediction System - Project Cleanup Script
# Safely cleans up development files and prepares for GitHub

echo "🏎️ F1 Prediction System - Project Cleanup"
echo "=========================================="

# Function to ask for confirmation
confirm() {
    read -p "$1 (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        return 0
    else
        return 1
    fi
}

# 1. Remove __pycache__ directories
echo "🗂️  Checking for __pycache__ directories..."
pycache_dirs=$(find . -type d -name "__pycache__" 2>/dev/null)
if [ ! -z "$pycache_dirs" ]; then
    echo "Found __pycache__ directories:"
    echo "$pycache_dirs"
    if confirm "Remove all __pycache__ directories?"; then
        find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
        echo "✅ Removed __pycache__ directories"
    fi
else
    echo "✅ No __pycache__ directories found"
fi

# 2. Remove .pyc files
echo "🐍 Checking for .pyc files..."
pyc_files=$(find . -name "*.pyc" 2>/dev/null)
if [ ! -z "$pyc_files" ]; then
    echo "Found .pyc files:"
    echo "$pyc_files" | head -10
    if [ $(echo "$pyc_files" | wc -l) -gt 10 ]; then
        echo "... and $(( $(echo "$pyc_files" | wc -l) - 10 )) more"
    fi
    if confirm "Remove all .pyc files?"; then
        find . -name "*.pyc" -delete
        echo "✅ Removed .pyc files"
    fi
else
    echo "✅ No .pyc files found"
fi

# 3. Remove empty directories
echo "📁 Checking for empty directories..."
empty_dirs=$(find . -type d -empty 2>/dev/null | grep -v ".git" | grep -v "venv")
if [ ! -z "$empty_dirs" ]; then
    echo "Found empty directories:"
    echo "$empty_dirs"
    if confirm "Remove empty directories?"; then
        find . -type d -empty -delete 2>/dev/null
        echo "✅ Removed empty directories"
    fi
else
    echo "✅ No empty directories found"
fi

# 4. Find large files
echo "📏 Checking for large files (>5MB)..."
large_files=$(find . -type f -size +5M 2>/dev/null | grep -v ".git" | grep -v "venv")
if [ ! -z "$large_files" ]; then
    echo "⚠️  Large files found (should not go to GitHub):"
    for file in $large_files; do
        size=$(ls -lh "$file" | awk '{print $5}')
        echo "  $file ($size)"
    done
    echo ""
    echo "💡 Consider adding these to .gitignore or storing externally"
else
    echo "✅ No large files found"
fi

# 5. Check for sensitive data
echo "🔐 Checking for potential sensitive data..."
sensitive_patterns="api_key|password|token|secret|API_KEY|PASSWORD|TOKEN|SECRET"
sensitive_files=$(grep -r -l -E "$sensitive_patterns" . --exclude-dir=venv --exclude-dir=.git --exclude="*.log" 2>/dev/null | grep -v cleanup.sh)
if [ ! -z "$sensitive_files" ]; then
    echo "⚠️  Files potentially containing sensitive data:"
    echo "$sensitive_files"
    echo ""
    echo "💡 Review these files before committing to GitHub"
else
    echo "✅ No obvious sensitive data patterns found"
fi

# 6. Create clean project structure summary
echo ""
echo "📋 CLEAN PROJECT STRUCTURE:"
echo "=========================="
tree -I 'venv|__pycache__|*.pyc|.git|archive|backend|frontend|nginx' -L 3 2>/dev/null || {
    echo "f1-prediction-system/"
    echo "├── app.py                 # ✅ Main Flask application"
    echo "├── requirements.txt       # ✅ Python dependencies" 
    echo "├── README.md             # ✅ Professional documentation"
    echo "├── .gitignore            # ✅ Git ignore rules"
    echo "├── cleanup.sh            # ✅ This cleanup script"
    echo "├── data/"
    echo "│   └── download_data.py  # ✅ FastF1 data fetcher"
    echo "├── notebooks/"
    echo "│   ├── train_model.ipynb # ✅ Model training"
    echo "│   └── research_analysis.ipynb # ✅ Statistical analysis"
    echo "├── scripts/"
    echo "│   ├── demo.py           # ✅ Command-line demo"
    echo "│   └── run_demo.sh       # ✅ One-command launcher"
    echo "└── docs/"
    echo "    └── images/           # 📷 Screenshots (add your app screenshot!)"
}

echo ""
echo "📝 RECOMMENDED ACTIONS:"
echo "======================"
echo "✅ Keep these essential files:"
echo "   • app.py (main application)"
echo "   • requirements.txt (dependencies)"
echo "   • README.md (documentation)"
echo "   • notebooks/ (research analysis)"
echo "   • scripts/ (demo tools)"
echo "   • data/download_data.py (data fetcher)"

echo ""
echo "🗑️  Consider removing/archiving:"
echo "   • backend/ (complex Docker setup not needed for simple version)"
echo "   • frontend/ (React separate from Flask app)"
echo "   • nginx/ (production deployment files)"
echo "   • docker-compose.*.yml (keep simple for GitHub)"
echo "   • .env.* files (may contain sensitive data)"

echo ""
echo "📸 TODO - Add screenshot:"
echo "   • Take a screenshot of your running app"
echo "   • Save as: docs/images/f1-predictor-screenshot.png"
echo "   • This will make your README look professional!"

echo ""
echo "🎯 NEXT STEPS:"
echo "=============="
echo "1. Review large files and sensitive data warnings above"
echo "2. Take a screenshot of your app for docs/images/"
echo "3. Test fresh install: deactivate && rm -rf venv && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt && python app.py"
echo "4. Create GitHub repository and push!"

echo ""
echo "✨ Cleanup complete! Your F1 prediction project is ready for the world! 🏁"