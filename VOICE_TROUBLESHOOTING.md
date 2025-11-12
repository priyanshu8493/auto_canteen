# Voice Not Activating - Troubleshooting Guide

## Summary of Changes Made

The voice system was not activating due to browser security policies and reverse proxy configuration issues. Here's what was fixed:

### 1. **Browser Security Context**
- Modern browsers require explicit user interaction to activate Web Audio API and Speech Synthesis
- The page now has buttons to explicitly enable audio instead of relying on autoplay
- Added support for multiple interaction types (click, touch, keyboard)

### 2. **Reverse Proxy Headers**
- Updated the WSGI middleware to properly handle `X-Forwarded-Proto` headers from Nginx
- This ensures the app correctly recognizes the HTTPS connection from Cloudflare
- Without this, the browser might not recognize the connection as "secure" and blocks audio APIs

### 3. **Socket.IO Configuration**
- Added proper configuration for Socket.IO to work with Nginx reverse proxy
- Configured websocket upgrade headers and timeout settings
- Socket.IO now explicitly specifies the socket.io path for the subpath deployment

### 4. **Audio Context Management**
- Added automatic resumption of suspended audio contexts
- Improved voice detection with multiple retry attempts
- Better fallback to visual and beep alerts if voice fails

## Steps to Fix Voice on Your Raspberry Pi

### Step 1: Update Your Nginx Configuration
Copy the provided `nginx.conf.example` and adapt it to your setup:

```bash
sudo cp /path/to/auto_canteen/nginx.conf.example /etc/nginx/sites-available/auto_canteen
sudo ln -s /etc/nginx/sites-available/auto_canteen /etc/nginx/sites-enabled/auto_canteen
sudo nginx -t  # Test configuration
sudo systemctl reload nginx
```

**Key points for your Nginx config:**
- Make sure `proxy_set_header X-Forwarded-Proto $scheme;` is set
- Ensure WebSocket headers are present:
  ```
  proxy_set_header Upgrade $http_upgrade;
  proxy_set_header Connection "Upgrade";
  ```
- The Socket.IO specific location block is important

### Step 2: Test the Application
1. Navigate to `https://your-domain.com/auto_canteen/counter`
2. Check the browser console (F12 → Console) for any errors
3. Click the **"Enable Audio"** button
4. You should hear "Audio activated. System ready for voice announcements."

### Step 3: Check Browser Requirements
On the counter page, you'll see logging information:
- Look at the console (F12) for messages like:
  - `Is secure context: true` ✅
  - `Voices available: X` ✅
  - `Audio context initialized successfully` ✅

If you see:
- `Is secure context: false` ❌ → Check Nginx headers
- `No voices available` ❌ → See Voice Package Installation below
- `Audio context not supported` ❌ → Browser doesn't support Web Audio API

### Step 4: Install Voice Packages (Raspberry Pi)
On Raspberry Pi OS, you may need to install speech synthesis packages:

```bash
# For Raspberry Pi with espeak
sudo apt-get update
sudo apt-get install espeak espeak-ng

# For better quality
sudo apt-get install festival festival-dev
```

After installation, restart your Flask app:
```bash
# If using systemd
sudo systemctl restart auto-canteen

# Or manually
pkill -f "python.*app.py"
# Then restart your Flask app
```

## Testing Checklist

- [ ] Open counter page on Raspberry Pi
- [ ] Open browser console (F12)
- [ ] Click "Enable Audio" button
- [ ] Verify message appears: "Audio activated. System ready..."
- [ ] Wait for a meal scan to test voice announcement
- [ ] If no voice: Click "Test Voice" button
- [ ] Check console for error messages

## Console Error Messages and Solutions

### Error: "No voices available after multiple attempts"
**Solution:** Install speech synthesis packages (see Step 4 above)

### Error: "Is secure context: false"
**Solution:** 
- Check your Nginx headers are correctly set
- Ensure `X-Forwarded-Proto: https` is being sent
- Test with: `curl -i https://your-domain/auto_canteen/counter | grep X-Forwarded`

### Error: "Socket.IO connection error"
**Solution:**
- Verify Nginx WebSocket headers are set
- Check Cloudflare settings → Speed → Rocket Loader should be OFF
- Check Cloudflare → Network Settings → WebSocket should be Enabled

### Error: "Audio context not supported"
**Solution:** This browser/device doesn't support Web Audio API. Voice will fall back to visual alerts (green flash on screen).

## Cloudflare Configuration

To ensure Cloudflare doesn't interfere with your setup:

1. **Speed Settings:**
   - Rocket Loader: **OFF** (interferes with JavaScript)
   - Minify: Be careful with JS minification

2. **Network Settings:**
   - WebSocket: **Enabled**
   - HTTP/2 to Origin: Enable if your origin supports it

3. **Cache Rules:**
   - Consider disabling cache for `/auto_canteen/` or setting cache level to "Bypass"

## Manual Testing via Command Line

SSH into your Raspberry Pi and test audio directly:

```bash
# Test espeak
espeak "Test voice system working"

# Test that the Flask app starts correctly
python3 /path/to/auto_canteen/app.py

# Check if Flask is listening
curl -k https://localhost:5000/auto_canteen/counter
```

## If Voice Still Doesn't Work

1. **Check the logs:**
   ```bash
   tail -f /path/to/auto_canteen/auto_canteen.log
   ```

2. **Enable verbose console output:**
   Open browser DevTools (F12) → Console tab
   Look for all messages starting with `console.log`

3. **Test visual alerts:**
   Click "Test Voice" button - you should see a green flash on screen
   This confirms at least the visual fallback is working

4. **Create a test script on Raspberry Pi:**
   ```python
   from gtts import gTTS  # If you want to try Google TTS
   tts = gTTS("Test", lang='en')
   tts.save("test.mp3")
   ```

## Performance Considerations for Raspberry Pi

The changes include:
- **Minimal overhead** - just voice detection and activation logic
- **Fallback mechanisms** - visual alerts if audio fails
- **Network efficient** - Socket.IO with appropriate timeout settings

Your Raspberry Pi 4B Plus should handle this without issues.

---

**Need more help?** Check the browser console (F12 → Console tab) - the code includes extensive logging to help diagnose issues.
