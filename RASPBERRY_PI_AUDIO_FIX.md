# Raspberry Pi Audio Fix - Complete Setup Guide

## Problem Summary
Audio is not working on Raspberry Pi 4B Plus counter page. The system needs explicit audio initialization and proper TTS package installation.

## Root Causes Identified
1. **Missing espeak package** - Server-side TTS not available
2. **No audio device routing** - Raspberry Pi needs explicit output device configuration
3. **Browser voice synthesis not initialized** - Voices load asynchronously, needs multiple retry attempts
4. **Audio context not resumed** - Suspended audio context wasn't being properly activated
5. **Fallback TTS not working** - The server-side TTS endpoint had issues

## Fixed Issues in This Update

### 1. **app.py - TTS Endpoint Improvements**
✅ Added robust espeak command with amplitude and speed optimization
✅ Added explicit file verification (checks file wasn't empty)
✅ Improved error handling with detailed logging
✅ Added festival fallback with text2wave
✅ Proper cache headers to ensure audio plays immediately
✅ Full traceback logging for debugging

**Key Changes:**
```python
espeak_cmd = ['espeak', '-w', temp_file, '-a', '200', '-s', '150', text]
# -a: amplitude (loudness)
# -s: speed in words per minute
```

### 2. **counter.html - Browser Voice System**
✅ Better voice detection with up to 10 retry attempts (was 5)
✅ Improved audio context resumption
✅ Prioritized voice selection (US English > English > default)
✅ Added 2-second fallback timeout to server TTS
✅ Enhanced error handling with specific error codes
✅ Better logging with platform and user agent info

**Key Changes:**
```javascript
// Retry voice loading up to 10 times
if (voices.length === 0 && voiceCheckCount < 10) {
    setTimeout(checkVoices, 200);  // Faster retry interval
}

// Timeout fallback to server TTS
setTimeout(() => {
    if (!speechStarted) {
        speakViaAPI(text);
    }
}, 2000);
```

### 3. **counter.html - Server TTS Fallback**
✅ Comprehensive audio element configuration
✅ Web Audio API fallback using arraybuffer
✅ Better error handling with multiple fallback mechanisms
✅ Enhanced logging for debugging

**Key Changes:**
```javascript
// Multiple fallback attempts:
// 1. Try HTML5 Audio element
// 2. Try Web Audio API with fetch
// 3. Show visual alert
```

### 4. **counter.html - Socket.IO Improvements**
✅ Better path calculation for subpath deployments
✅ Added Raspberry Pi specific timeout settings
✅ Better transport selection (websocket > polling)
✅ Enhanced disconnect reason logging

## Installation Steps

### Step 1: Install Audio Packages on Raspberry Pi
SSH into your Raspberry Pi and run:

```bash
# Update package list
sudo apt-get update

# Install espeak (essential for voice)
sudo apt-get install espeak espeak-ng -y

# Install festival (optional but recommended for quality)
sudo apt-get install festival festival-dev -y

# Test espeak
espeak "Voice system activated successfully"
```

If you hear the voice message clearly, espeak is working!

### Step 2: Configure Audio Output Device (if needed)
If you have speakers connected via USB or AUX:

```bash
# List audio devices
aplay -l

# Set default audio device (example for USB):
# Edit ~/.asoundrc or use pactl

# Test audio output
speaker-test -c2 -l5 -twav

# You should hear pink noise in a loop
```

For USB speakers specifically:
```bash
# Find your USB device
aplay -l

# Example output:
# **** List of PLAYBACK Hardware Devices ****
# card 0: b1 [USB Audio Device], device 0: USB Audio [USB Audio]

# Create ~/.asoundrc
cat > ~/.asoundrc << EOF
defaults.pcm.card 0
defaults.ctl.card 0
EOF
```

### Step 3: Update and Restart Flask App
On your Raspberry Pi:

```bash
# Pull latest code
cd /path/to/auto_canteen
git pull origin main

# If using systemd:
sudo systemctl restart auto-canteen

# Or if running manually:
pkill -f "python.*app.py"
python3 app.py  # or however you normally start it
```

### Step 4: Test Audio System

1. **Open counter page on Raspberry Pi browser:**
   - Navigate to: `https://your-domain/auto_canteen/counter`
   - Open browser console (F12 → Console)

2. **Look for these log messages:**
   ```
   ✅ Is secure context: true
   ✅ Voice check X: N voices found
   ✅ Audio context initialized successfully
   ✅ Connected to server via Socket.IO
   ```

3. **Click "Enable Audio" button**
   - You should hear: "Audio activated. System ready for voice announcements."
   - Status shows: "Voice activated - System ready"

4. **Click "Test Voice" button**
   - You should hear: "Voice test. Counter system is working."

5. **Trigger a meal scan**
   - Voice should announce: "Meal served. Total: X"

## Troubleshooting

### Issue: "No voices available after multiple attempts"
**Solution:**
```bash
# Install espeak
sudo apt-get install espeak espeak-ng -y

# Test it
espeak "Test voice"

# Restart Flask
sudo systemctl restart auto-canteen
```

### Issue: "Is secure context: false"
**Solution:**
- Check your Nginx configuration has: `proxy_set_header X-Forwarded-Proto $scheme;`
- Make sure you're accessing via HTTPS
- Check Cloudflare settings → SSL/TLS mode should be "Full"

### Issue: Audio plays but very quietly
**Solution:**
```bash
# Adjust volume
amixer set PCM 100%
alsamixer  # Interactive volume control

# In Flask app logs, you'll see the espeak command
# Current amplitude is 200 (max is 200)
# Speed is 150 wpm
```

### Issue: Audio plays through wrong device
**Solution:**
```bash
# List devices
aplay -l

# Set default device in ~/.asoundrc
cat ~/.asoundrc

# Example for USB device:
defaults.pcm.card 0  # or card 1, depends on aplay -l output
defaults.ctl.card 0

# Restart Flask
sudo systemctl restart auto-canteen
```

### Issue: TTS Endpoint Returns 501 Error
**Check Flask logs:**
```bash
# View recent logs
sudo journalctl -u auto-canteen -n 50 -f

# Look for messages like:
# CRITICAL: No TTS system available (espeak and festival not installed)
# On Raspberry Pi, install with: sudo apt-get install espeak espeak-ng
```

**Or check app logs:**
```bash
tail -f /path/to/auto_canteen/auto_canteen.log
```

### Issue: Socket.IO Says "Offline - No Connection"
**Check browser console (F12):**
- Look for "Socket.IO connection error"
- Check Flask logs for connection issues
- Verify Nginx Socket.IO configuration

**Solution:**
```bash
# Check Nginx configuration
sudo cat /etc/nginx/sites-enabled/auto-canteen

# Should have these for Socket.IO:
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "Upgrade";
proxy_read_timeout 86400;
proxy_send_timeout 86400;

# Reload Nginx
sudo nginx -t && sudo systemctl reload nginx
```

## Console Logging Reference

When troubleshooting, these are the messages you should see in order:

1. **Initialization:**
   ```
   Initializing audio system...
   Is secure context: true
   Protocol: https:
   Platform: Linux armv7l
   Audio context initialized successfully
   Audio context state: suspended
   Voice check 1: 0 voices found
   Voice check 2: 0 voices found
   Voice check 3: N voices found
   Voices loaded successfully: N
   ```

2. **First User Interaction:**
   ```
   Enabling audio...
   Audio context state: suspended
   Attempting to resume audio context...
   ✅ Audio context resumed successfully
   ```

3. **Test Voice Click:**
   ```
   Enabling audio...
   Browser voice available, testing...
   Attempting browser speech synthesis for: Audio activated...
   Speech started: Audio activated...
   Speech ended
   ```

4. **Counter Update:**
   ```
   Counter update received: {count: 5}
   Attempting browser speech synthesis for: Meal served. Total: 5
   OR
   Using server-side TTS fallback...
   Fetching TTS from: /auto_canteen/api/speak?text=...
   Server TTS: Playback started
   ```

## Server-Side Debugging

SSH into your Raspberry Pi and test TTS directly:

```bash
# Test espeak directly
espeak "Testing voice system"

# Test the Flask API endpoint
curl "https://localhost:5000/auto_canteen/api/speak?text=hello+world" -o test.wav
aplay test.wav  # Play it

# Check Flask app is running
ps aux | grep python
ps aux | grep app.py

# Check Flask logs
tail -f /path/to/auto_canteen/auto_canteen.log

# Check systemd logs if using systemd
sudo journalctl -u auto-canteen -n 100 -f
```

## Performance Notes

- **espeak:** Fast, good for Raspberry Pi, may sound robotic
- **festival:** Slower, more natural voice, higher CPU usage
- **Browser speech synthesis:** Best quality if voices are available
- **Server TTS fallback:** Reliable backup for Raspberry Pi

## Audio Quality Tips

For better audio quality on Raspberry Pi:

1. **Adjust espeak parameters in app.py:**
   ```python
   espeak_cmd = ['espeak', '-w', temp_file, '-a', '200', '-s', '150', text]
   # -a: amplitude 0-200 (increase for louder)
   # -s: speed in words per minute (slower = 130-150, faster = 180+)
   ```

2. **Use festival for better voice:**
   ```bash
   sudo apt-get install festival festival-dev
   # Uncomment festival fallback in code
   ```

3. **Adjust volume at system level:**
   ```bash
   alsamixer  # GUI volume control
   amixer set PCM 100%  # Set to maximum
   ```

## Next Steps

After completing these steps:
1. ✅ Audio packages installed
2. ✅ Flask app restarted
3. ✅ "Enable Audio" button works
4. ✅ "Test Voice" produces sound
5. ✅ Counter updates trigger announcements

If you still have issues, create a GitHub issue with:
- Output from browser console (F12)
- Output from Flask logs
- Output from `espeak "test"` command
- Raspberry Pi model and OS version

## Files Modified

- `app.py` - Enhanced TTS endpoint with better error handling
- `templates/counter.html` - Improved audio initialization and fallback system
- This guide: `RASPBERRY_PI_AUDIO_FIX.md`

All changes are backward compatible and don't affect other functionality.
