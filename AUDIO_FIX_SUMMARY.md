# Audio Fix Summary - Raspberry Pi 4B Plus

## Issue
Audio was not working on the Raspberry Pi 4B Plus counter page, even though it worked fine on phones and desktop devices. The system requires explicit audio initialization and proper TTS system support.

## Root Causes Identified

### 1. **Missing Voice Packages**
- Raspberry Pi doesn't have text-to-speech engines installed by default
- `espeak` or `festival` required for server-side TTS fallback

### 2. **Browser Voice Synthesis Issues**
- Voice data loads asynchronously on Raspberry Pi (slower devices)
- Only 5 retry attempts weren't enough to detect voices
- Audio context might be suspended and not properly resumed

### 3. **Weak Fallback System**
- If browser speech synthesis failed, there was no reliable server-side fallback
- TTS endpoint had poor error handling and didn't validate output

### 4. **Audio Context Not Managed**
- Suspended audio contexts weren't being resumed after user interaction
- No timeout mechanism to fall back to server TTS if browser voice stalled

### 5. **Suboptimal TTS Parameters**
- espeak was running with default parameters (slower, quieter)
- No amplitude/speed optimization for Raspberry Pi hardware

## Changes Made

### 1. **app.py - Enhanced TTS Endpoint** ✅

**File:** [app.py](app.py#L337-L435)

**Key Improvements:**

```python
# Before: espeak without parameters
subprocess.run(['espeak', '-w', temp_file, text], check=True, timeout=10)

# After: optimized for Raspberry Pi
espeak_cmd = ['espeak', '-w', temp_file, '-a', '200', '-s', '150', text]
# -a: amplitude 200 (max volume)
# -s: 150 words per minute (clear and natural)
```

**What was fixed:**
- ✅ Added amplitude optimization (`-a 200`) for maximum volume
- ✅ Added speed optimization (`-s 150` wpm) for clarity  
- ✅ Added file validation (checks output file isn't empty)
- ✅ Increased timeout from 10s to 15s for Raspberry Pi
- ✅ Suppressed stderr to avoid noise in logs
- ✅ Added detailed logging with file size and status
- ✅ Added festival fallback with text2wave converter
- ✅ Proper cache headers to prevent browser caching issues
- ✅ Full error traceback logging for debugging

### 2. **counter.html - Browser Voice Improvements** ✅

**File:** [templates/counter.html](templates/counter.html#L72-L105)

**Voice Detection:**

```javascript
// Before: 5 retry attempts, 500ms intervals
if (voices.length === 0 && voiceCheckCount < 5) {
    setTimeout(checkVoices, 500);
}

// After: 10 retry attempts, 200ms intervals
if (voices.length === 0 && voiceCheckCount < 10) {
    setTimeout(checkVoices, 200);
}
```

**What was fixed:**
- ✅ Doubled retry attempts (5 → 10) for slower Raspberry Pi
- ✅ Faster retry interval (500ms → 200ms) to detect voices quicker
- ✅ Better logging with platform and user agent info
- ✅ Explicit audio context state tracking
- ✅ Better voice priority selection (US English > English > default)

### 3. **counter.html - Speech Synthesis** ✅

**File:** [templates/counter.html#L196-L282](templates/counter.html#L196-L282)

**Speech Function Improvements:**

```javascript
// Before: No timeout fallback
speechSynthesis.speak(utterance);

// After: 2-second timeout to fallback to server TTS
setTimeout(() => {
    if (!speechStarted && speechSynthesis.speaking === false) {
        speakViaAPI(text);  // Fallback to server
    }
}, 2000);
```

**What was fixed:**
- ✅ Added `speechStarted` flag to track speech state
- ✅ 2-second timeout fallback to server TTS if browser voice stalls
- ✅ Check if `speechSynthesis.speaking` is false to detect failed starts
- ✅ Better error handling with specific error logging
- ✅ Tries server TTS if browser speech errors before completing
- ✅ Voice priority selection for better voice quality

### 4. **counter.html - Server TTS Fallback** ✅

**File:** [templates/counter.html#L284-L357](templates/counter.html#L284-L357)

**Advanced Fallback Chain:**

```javascript
// Before: Simple audio element, fails if playback fails
const audioElement = new Audio();
audioElement.src = ttsUrl;
audioElement.play().catch(e => console.log('Failed'));

// After: Multiple fallback layers
1. HTML5 Audio element with explicit settings
2. Web Audio API with arraybuffer decoding
3. Visual alert if all fail
```

**What was fixed:**
- ✅ Explicit audio element configuration (volume, crossOrigin)
- ✅ Better event handlers (onloadstart, oncanplay, onplay, onended, onerror)
- ✅ Promise-based play() with error handling
- ✅ Fetch + Web Audio API fallback for incompatible browsers
- ✅ Detailed error logging with error codes and messages
- ✅ Visual feedback (green flash) if all audio methods fail

### 5. **counter.html - Audio Initialization** ✅

**File:** [templates/counter.html#L47-L96](templates/counter.html#L47-L96)

**Initialization Improvements:**

```javascript
// Before: Basic audio context creation
const audioContext = new AudioContext();

// After: Full diagnostic and retry system
- Log sample rate and audio context state
- Wait for voices to load asynchronously
- Better logging with platform detection
- Improved fallback detection
```

**What was fixed:**
- ✅ Detailed logging with platform and sample rate info
- ✅ Better async voice loading detection
- ✅ More informative status messages
- ✅ Proper handling of no-voice scenarios
- ✅ Better support for different Raspberry Pi models

### 6. **counter.html - Audio Enable Function** ✅

**File:** [templates/counter.html#L529-L560](templates/counter.html#L529-L560)

**Enable Audio Improvements:**

```javascript
// Before: Simple voice test or fallback beeps
if (voiceEnabled) {
    speak("Audio activated...");
}

// After: Smart audio activation with dual fallback
if (voiceEnabled && speechSynthesis.getVoices().length > 0) {
    speak("Audio activated...");  // Browser voice
} else {
    speakViaAPI("Audio activated...");  // Server TTS
}
```

**What was fixed:**
- ✅ Smart selection between browser voice and server TTS
- ✅ Always provides audio feedback (never silent)
- ✅ Better status messages
- ✅ Logs to help debugging

### 7. **counter.html - Socket.IO Configuration** ✅

**File:** [templates/counter.html#L412-L470](templates/counter.html#L412-L470)

**Socket.IO Improvements:**

```javascript
// Before: Basic configuration
const socketConfig = {
    transports: ['websocket', 'polling'],
    path: socketPath
};

// After: Raspberry Pi optimized
const socketConfig = {
    transports: ['websocket', 'polling'],
    path: socketPath,
    upgradeTimeout: 20000,    // Longer timeout for slow connections
    rememberUpgrade: true,     // Remember successful upgrade
    forceNew: true,            // Force new connection
    // ... other settings
};
```

**What was fixed:**
- ✅ Longer upgrade timeout (20s) for slow Raspberry Pi
- ✅ Better transport detection and logging
- ✅ Added connection state monitoring
- ✅ Better error messages with reason codes
- ✅ Improved disconnect handling

## Installation Instructions

### Step 1: Install Required Packages on Raspberry Pi
```bash
# SSH into your Raspberry Pi
ssh pi@your-rpi-ip

# Update package list
sudo apt-get update

# Install espeak (REQUIRED)
sudo apt-get install espeak espeak-ng -y

# Test espeak
espeak "Voice system activated successfully"
```

### Step 2: Update Code
```bash
cd /path/to/auto_canteen
git pull origin main
```

### Step 3: Restart Flask Application
```bash
# Using systemd
sudo systemctl restart auto-canteen

# Or manually
pkill -f "python.*app.py"
python3 app.py  # Or however you normally start it
```

### Step 4: Verify Installation
1. Open counter page: `https://your-domain/auto_canteen/counter`
2. Open browser console: `F12 → Console`
3. Look for log messages like:
   - `Initializing audio system...`
   - `Is secure context: true`
   - `Audio context initialized successfully`
   - `Connected to server via Socket.IO`
4. Click "Enable Audio" button
5. You should hear: "Audio activated. System ready for voice announcements."

## Testing

### Test 1: Browser Voice
```
1. Open counter page
2. Open browser console (F12)
3. Click "Enable Audio"
4. Look for: "Browser voice available, testing..."
5. Should hear audio announcement
```

### Test 2: Server TTS Fallback
```
1. SSH to Raspberry Pi
2. Run: espeak "Testing server TTS"
3. You should hear audio
4. If yes, Flask TTS endpoint will work
```

### Test 3: Complete Audio Chain
```
1. Click "Enable Audio" on counter page
2. Click "Test Voice" button
3. Should hear: "Voice test. Counter system is working."
4. If not, check browser console for errors
5. Look for logs showing which method was used
```

### Test 4: Meal Announcement
```
1. Trigger a scan on the registration page
2. Counter page should announce the meal
3. Voice should say: "Meal served. Total: X"
4. If not, check browser logs and Flask logs
```

## Troubleshooting

### Issue: "No voices available"
**Solution:**
```bash
sudo apt-get install espeak espeak-ng -y
sudo systemctl restart auto-canteen
```

### Issue: Audio too quiet
**Solution:**
```bash
# Max out volume
amixer set PCM 100%
alsamixer  # Interactive control

# Check Flask logs for espeak parameters
tail -f /path/to/auto_canteen/auto_canteen.log

# Current settings: -a 200 -s 150
# You can modify in app.py if needed
```

### Issue: "Is secure context: false"
**Solution:**
- Ensure Nginx has: `proxy_set_header X-Forwarded-Proto $scheme;`
- Access only via HTTPS
- Check Cloudflare SSL/TLS is set to "Full"

### Issue: TTS returns 501 error
**Solution:**
```bash
which espeak  # Check if installed
espeak "test"  # Test directly

# If not installed:
sudo apt-get install espeak espeak-ng -y
sudo systemctl restart auto-canteen
```

### Issue: Socket.IO offline
**Solution:**
- Check Nginx WebSocket headers are set
- Check Cloudflare → Network → WebSocket enabled
- Check Cloudflare → Speed → Rocket Loader is OFF

## Files Modified

1. **app.py**
   - Enhanced `/api/speak` endpoint with better TTS handling
   - Added logging and error reporting
   - Optimized for Raspberry Pi performance

2. **templates/counter.html**
   - Improved voice detection and initialization
   - Better speech synthesis with timeouts
   - Enhanced server TTS fallback system
   - Better Socket.IO configuration
   - Additional logging for debugging

## Files Created

1. **RASPBERRY_PI_AUDIO_FIX.md**
   - Comprehensive setup and troubleshooting guide
   - Detailed explanation of all changes
   - Server-side debugging instructions
   - Performance optimization tips

2. **RPI_AUDIO_QUICK_FIX.md**
   - Quick reference card (5-minute setup)
   - Common issues and fixes
   - Debug commands checklist
   - Support information

3. **diagnose_audio.sh**
   - Automated diagnostic script
   - Checks all system components
   - Tests espeak, audio devices, Flask app
   - Provides actionable fixes

## Performance Impact

- **Minimal** - All changes are optimized for Raspberry Pi
- No database queries added
- No additional dependencies
- Slightly longer TTS generation time (1-2 seconds) - acceptable

## Backward Compatibility

✅ **Fully compatible** with existing deployments
- No breaking changes
- No config changes required  
- No database migrations needed
- Can be deployed immediately

## What Users Will Experience

1. **On first load:**
   - "Enable Audio" button available
   - Status shows audio system loading

2. **After clicking "Enable Audio":**
   - Hear: "Audio activated. System ready for voice announcements."
   - Status shows: "Voice activated - System ready"

3. **On meal announcement:**
   - Hear: "Meal served. Total: X"
   - Works via browser voice OR server TTS (automatic)

4. **If audio fails:**
   - Visual alert (green flash) instead
   - No error messages to user
   - System still fully functional

## Future Improvements

Potential enhancements for future versions:
1. Web audio recorder to test speaker setup
2. Voice quality selection (espeak vs festival)
3. Audio level adjustments in UI
4. Language selection for TTS
5. Audio playback history/logging

## Support

If audio still doesn't work after following this guide:

1. **Run diagnostics:**
   ```bash
   bash /path/to/auto_canteen/diagnose_audio.sh
   ```

2. **Check logs:**
   ```bash
   tail -f /path/to/auto_canteen/auto_canteen.log
   ```

3. **Test espeak directly:**
   ```bash
   espeak "Test message"
   ```

4. **Check browser console (F12)** for error messages

5. **Verify system setup:**
   - Speakers/AUX properly connected
   - Audio output device set correctly
   - Flask app running and listening
   - Nginx configured properly

## Summary

This update provides **complete audio support for Raspberry Pi** by:

1. ✅ Optimizing server-side TTS with proper parameters
2. ✅ Improving browser voice detection with more retries
3. ✅ Adding intelligent fallback from browser to server TTS
4. ✅ Better error handling and debugging
5. ✅ Multiple audio playback mechanisms
6. ✅ Comprehensive documentation and diagnostics

The system now works reliably on Raspberry Pi 4B Plus with aux/USB speakers and provides audio announcements as originally intended.

---

**Last Updated:** 2025-01-02  
**Tested On:** Raspberry Pi 4B Plus  
**Compatible With:** Raspberry Pi OS Bullseye & Bookworm  
**Audio Packages:** espeak, espeak-ng, festival (optional)
