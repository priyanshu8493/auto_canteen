# Voice Activation - Quick Reference

## 🎯 What Changed?
Voice wasn't working due to browser security policies + Nginx configuration. Now fixed!

## ✅ How to Activate Voice

### On Counter Page
1. **Click "Enable Audio" button** ← Required step!
2. You'll hear: "Audio activated. System ready for voice announcements."
3. Counter will now announce meals via voice
4. Green flash indicates fallback visual alert

### Testing Voice
- Click **"Test Voice"** button to hear a test message
- Or scan a meal (QR code) to hear announcement

## 🔧 If Voice Doesn't Work

### Quick Checks (30 seconds)
1. Open browser console: **F12 → Console tab**
2. Look for these messages:
   - ✅ `Is secure context: true` 
   - ✅ `Voices available: X`
   - ✅ `Audio context initialized successfully`
3. If any show ❌ or missing, see **Troubleshooting** below

### Troubleshooting

| Issue | Check | Solution |
|-------|-------|----------|
| "Is secure context: false" | Browser console | Fix Nginx `X-Forwarded-Proto` header |
| "No voices available" | Browser console | Install: `sudo apt-get install espeak` |
| "Audio context: suspended" | State doesn't change | Click "Enable Audio" button |
| Green flash but no sound | Visual fallback works | Install voice packages (Raspberry Pi) |
| Socket.IO won't connect | Console shows error | Check Nginx WebSocket headers |

## 📋 Setup Checklist

- [ ] Deploy updated code from git
- [ ] Restart Flask app: `sudo systemctl restart auto-canteen`
- [ ] Visit counter page: `https://your-domain/auto_canteen/counter`
- [ ] Click "Enable Audio" button
- [ ] Click "Test Voice" button and listen
- [ ] Scan a meal and verify announcement

## 🔍 Diagnostic Tool

Visit this URL to diagnose audio issues:
```
https://your-domain/auto_canteen/audio_diagnostic
```

This page will:
- ✅ Check browser environment
- ✅ Test audio APIs
- ✅ Check voice availability  
- ✅ Test network connectivity
- ✅ Provide detailed logs

## 🚀 Nginx Configuration

If voice still doesn't work, apply Nginx config from:
```
nginx.conf.example
```

Key requirements:
```nginx
# MUST have these headers:
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "Upgrade";
```

Then reload:
```bash
sudo nginx -t && sudo systemctl reload nginx
```

## 📚 Full Documentation

See these files for detailed information:
- `VOICE_FIX_SUMMARY.md` - What was fixed and why
- `VOICE_TROUBLESHOOTING.md` - Complete troubleshooting guide
- `nginx.conf.example` - Nginx configuration reference

## 🛠 Raspberry Pi Voice Packages

If "No voices available" error:
```bash
sudo apt-get update
sudo apt-get install espeak espeak-ng
# Restart Flask app
sudo systemctl restart auto-canteen
```

## 📞 Quick Help

**Voice still not working?**
1. Open diagnostic tool: `/audio_diagnostic`
2. Check all items are ✅
3. Click "Test Speech Synthesis" 
4. Check console for error messages
5. Refer to VOICE_TROUBLESHOOTING.md

**Nothing changed in counter page?**
1. Hard refresh: `Ctrl+Shift+R` (or `Cmd+Shift+R` on Mac)
2. Clear browser cache and reload
3. Check Flask app restarted: `curl https://your-domain/auto_canteen/counter`

---

**Remember:** Always click "Enable Audio" button first - modern browsers require user interaction to enable audio APIs.
