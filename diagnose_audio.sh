#!/bin/bash

# Auto Canteen Audio System Diagnostics
# Run this on your Raspberry Pi to identify audio issues

echo "================================"
echo "Auto Canteen Audio Diagnostics"
echo "================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

# Test 1: Check system
echo "[1/8] System Information"
echo "Platform: $(uname -a)"
echo "Raspberry Pi Model: $(cat /proc/device-tree/model 2>/dev/null || echo 'Unknown')"
echo ""

# Test 2: Check espeak installation
echo "[2/8] Checking espeak installation..."
if command -v espeak &> /dev/null; then
    echo -e "${GREEN}✅ espeak is installed${NC}"
    espeak --version
else
    echo -e "${RED}❌ espeak is NOT installed${NC}"
    echo "   Install with: sudo apt-get install espeak espeak-ng"
    ((ERRORS++))
fi
echo ""

# Test 3: Test espeak
echo "[3/8] Testing espeak audio output..."
if command -v espeak &> /dev/null; then
    if espeak "Test message" 2>/dev/null; then
        echo -e "${GREEN}✅ espeak works${NC}"
        echo "   Did you hear the voice? If not, check your speakers."
    else
        echo -e "${RED}❌ espeak failed to run${NC}"
        ((ERRORS++))
    fi
else
    echo -e "${YELLOW}⚠️  Skipping (espeak not installed)${NC}"
fi
echo ""

# Test 4: Check festival
echo "[4/8] Checking festival installation (optional)..."
if command -v text2wave &> /dev/null; then
    echo -e "${GREEN}✅ festival/text2wave is installed${NC}"
else
    echo -e "${YELLOW}⚠️  festival not installed (optional, but recommended)${NC}"
    echo "   Install with: sudo apt-get install festival festival-dev"
    ((WARNINGS++))
fi
echo ""

# Test 5: Check audio devices
echo "[5/8] Checking audio devices..."
if command -v aplay &> /dev/null; then
    echo "Available audio devices:"
    aplay -l
    echo ""
    echo "Default playback device info:"
    aplay -L | head -5
else
    echo -e "${YELLOW}⚠️  aplay not found${NC}"
    ((WARNINGS++))
fi
echo ""

# Test 6: Check Flask app status
echo "[6/8] Checking Flask application..."
if pgrep -f "python.*app.py" > /dev/null; then
    echo -e "${GREEN}✅ Flask app is running${NC}"
    PID=$(pgrep -f "python.*app.py")
    echo "   PID: $PID"
else
    echo -e "${YELLOW}⚠️  Flask app is not running${NC}"
    echo "   Start with: python3 app.py"
    ((WARNINGS++))
fi
echo ""

# Test 7: Check if app is listening
echo "[7/8] Checking Flask app is listening..."
if netstat -tlnp 2>/dev/null | grep -q "python"; then
    echo -e "${GREEN}✅ Flask app is listening${NC}"
    netstat -tlnp 2>/dev/null | grep python | head -3
elif ss -tlnp 2>/dev/null | grep -q "python"; then
    echo -e "${GREEN}✅ Flask app is listening${NC}"
    ss -tlnp 2>/dev/null | grep python | head -3
else
    echo -e "${YELLOW}⚠️  Cannot verify if Flask is listening (check manually)${NC}"
    ((WARNINGS++))
fi
echo ""

# Test 8: Check logs
echo "[8/8] Checking application logs..."
if [ -f "auto_canteen.log" ]; then
    echo "Recent log entries:"
    tail -n 5 auto_canteen.log
    
    # Check for TTS errors
    if grep -q "TTS error\|No TTS system\|espeak" auto_canteen.log 2>/dev/null; then
        echo ""
        echo "TTS-related log entries:"
        grep "TTS\|espeak\|festival" auto_canteen.log | tail -n 3
    fi
else
    echo -e "${YELLOW}⚠️  No auto_canteen.log file found${NC}"
fi
echo ""

# Summary
echo "================================"
echo "Diagnostics Summary"
echo "================================"
echo "Errors found: $ERRORS"
echo "Warnings found: $WARNINGS"
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Open browser console (F12) on counter page"
    echo "2. Click 'Enable Audio' button"
    echo "3. Click 'Test Voice' button"
    echo "4. You should hear audio"
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠️  Some optional features not configured${NC}"
    echo ""
    echo "System should still work, but consider installing:"
    echo "- festival (for better voice quality)"
    echo "- festival-dev (required for text2wave)"
else
    echo -e "${RED}❌ Some critical issues found${NC}"
    echo ""
    echo "Priority fixes:"
    
    if ! command -v espeak &> /dev/null; then
        echo "1. Install espeak: sudo apt-get install espeak espeak-ng -y"
    fi
    
    if ! pgrep -f "python.*app.py" > /dev/null; then
        echo "2. Start Flask app"
    fi
    
    echo ""
    echo "After fixing, run this script again."
fi

echo ""
echo "================================"
echo "Additional Debugging"
echo "================================"
echo ""
echo "To test TTS endpoint manually:"
echo "curl 'https://localhost:5000/auto_canteen/api/speak?text=hello' -k -o test.wav"
echo "aplay test.wav"
echo ""
echo "To view Flask logs in real-time:"
echo "tail -f auto_canteen.log"
echo ""
echo "To view systemd logs (if using systemd service):"
echo "sudo journalctl -u auto-canteen -f"
echo ""
echo "To test Socket.IO connection:"
echo "Check browser console (F12) for 'Connected to server' message"
echo ""
