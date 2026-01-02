# Raspberry Pi Audio - Quick Reference

## ⚡ 5-Minute Setup

```bash
# 1. Install espeak (REQUIRED)
sudo apt-get update
sudo apt-get install espeak espeak-ng -y

# 2. Test espeak
espeak "Voice test successful"

# 3. Go to app directory
cd /path/to/auto_canteen

# 4. Pull latest code
git pull origin main

# 5. Restart Flask
sudo systemctl restart auto-canteen

# 6. Test in browser
# Go to: https://your-domain/auto_canteen/counter
# Click: "Enable Audio" button
# Listen: for "Audio activated. System ready..."
```

## 🔊 Audio Test Checklist

- [ ] Open `/auto_canteen/counter` in Raspberry Pi browser
- [ ] Open browser console (F12)
- [ ] Click "Enable Audio" button
- [ ] Hear: "Audio activated. System ready for voice announcements."
- [ ] Click "Test Voice" button
- [ ] Hear: "Voice test. Counter system is working."
- [ ] Status shows: "Voice activated - System ready"
- [ ] Trigger meal scan
- [ ] Hear: "Meal served. Total: X"

## 🐛 Quick Debug Commands

```bash
# Test espeak
espeak "Voice system check"

# List audio devices
aplay -l

# Check Flask is running
ps aux | grep app.py

# View recent logs
tail -f /path/to/auto_canteen/auto_canteen.log

# Test TTS endpoint
curl "https://localhost:5000/auto_canteen/api/speak?text=hello" -o test.wav
aplay test.wav
```

## ❌ Common Issues & Fixes

### "No voices available"
```bash
sudo apt-get install espeak espeak-ng -y
sudo systemctl restart auto-canteen
```

### Audio too quiet
```bash
# Max volume
amixer set PCM 100%

# Check Flask logs for espeak command
tail -f /path/to/auto_canteen/auto_canteen.log
```

### "Is secure context: false"
- Check Nginx has: `proxy_set_header X-Forwarded-Proto $scheme;`
- Access via HTTPS only
- Check Cloudflare SSL mode is "Full"

### Socket.IO offline
- Check Nginx WebSocket headers
- Check Cloudflare → Network → WebSocket enabled
- Check Cloudflare → Speed → Rocket Loader OFF

### TTS returns 501 error
```bash
# Check if espeak is installed
which espeak

# If not:
sudo apt-get install espeak espeak-ng -y

# Test it
espeak "Works"

# Restart Flask
sudo systemctl restart auto-canteen
```

## 📋 Browser Console Messages

**Good signs:**
```
✅ Is secure context: true
✅ Audio context initialized successfully
✅ Connected to server via Socket.IO
✅ Voice check 3: 2 voices found
```

**Bad signs:**
```
❌ Is secure context: false  → Fix Nginx headers
❌ No voices available       → Install espeak
❌ Socket.IO connection error → Check WebSocket headers
```

## 🔧 Configuration Files

### Check Nginx Socket.IO Support
```bash
cat /etc/nginx/sites-enabled/auto-canteen
# Look for: Upgrade and Connection headers
```

### Check Flask is listening
```bash
sudo netstat -tlnp | grep python
# Should show port 5000
```

### Check log file permissions
```bash
ls -la /path/to/auto_canteen/auto_canteen.log
# Should be readable
```

## 🎯 What Changed in Latest Update

✅ **TTS Endpoint (app.py)**
- Added amplitude/speed optimization for Raspberry Pi
- Better error handling and logging
- Festival fallback support

✅ **Browser Voice (counter.html)**
- More aggressive voice detection (10 retries instead of 5)
- Fallback to server TTS after 2 seconds
- Better audio context resumption
- Enhanced error logging

✅ **Server TTS Fallback (counter.html)**
- Web Audio API support for arraybuffer playback
- Multiple fallback mechanisms
- Better error handling

## 📞 Support Info

If audio still doesn't work after following this guide:

1. Check Flask logs:
   ```bash
   tail -n 100 /path/to/auto_canteen/auto_canteen.log
   ```

2. Check browser console (F12):
   - Screenshot the console output
   - Look for error messages starting with ❌

3. Verify system setup:
   ```bash
   espeak "Test"                    # Should hear voice
   ps aux | grep app.py              # Flask should be running
   curl https://localhost/auto_canteen/counter  # Should load
   ```

4. Check Nginx reverse proxy:
   ```bash
   sudo nginx -t                     # Should say OK
   curl -i localhost | grep X-Forwarded  # Should show headers
   ```

## 🚀 Performance Optimization

For faster response times:
```bash
# Check CPU load
top

# If high, consider:
# - Using espeak instead of festival (faster)
# - Reducing complexity in other areas
# - Monitoring background processes
```

## 📝 Notes

- All changes are backward compatible
- No database changes
- No configuration changes required
- Can be reverted by pulling previous commit if needed

---

**Last Updated:** 2025-01-02
**Compatible with:** Raspberry Pi 4B Plus, Raspberry Pi OS Bullseye/Bookworm
