# Quick Reference - Dual Device Counter System

## 🎯 What Was Implemented

### 1. Pop-ups & Voice Announcements on Scan ✅
- **What:** When a faculty member scans their QR code, a green pop-up appears showing their name with a checkmark
- **Where:** Both `/counter` and `/counter2` pages
- **Audio:** System announces "Meal served to [Faculty Name]"
- **Duration:** Pop-up appears for 3 seconds with smooth animations

### 2. Completely Separate Device 2 System ✅
- **Independent Database:** Device 2 has its own faculty, scans, and counter tables
- **Independent Endpoints:** Device 2 has its own URLs (/register2, /scan2, /counter2)
- **Independent Cookies:** Device 2 uses `faculty_id_2` instead of `faculty_id`
- **Independent Counters:** Device 1 and Device 2 maintain separate meal counts
- **Independent Socket Namespace:** Device 2 uses `/device2` namespace, Device 1 uses `/`

## 📱 How to Use

### Device 1 (Original):
```
Registration: https://yourdomain.com/register
Counter Display: https://yourdomain.com/counter
Reset Counter: Click "Reset Counter" button on counter page
```

### Device 2 (New):
```
Registration: https://yourdomain.com/register2
Counter Display: https://yourdomain.com/counter2
Reset Counter: Click "Reset Counter" button on counter2 page
```

## 🔧 Backend API Endpoints

### Device 1 Endpoints:
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/register` | POST | Register faculty for Device 1 |
| `/scan` | GET | QR code scan for Device 1 |
| `/counter` | GET | Display counter for Device 1 |
| `/api/counter` | GET | Get counter value (JSON) |
| `/reset-counter` | POST | Reset Device 1 counter |

### Device 2 Endpoints:
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/register2` | POST | Register faculty for Device 2 |
| `/scan2` | GET | QR code scan for Device 2 |
| `/counter2` | GET | Display counter for Device 2 |
| `/api/counter2` | GET | Get counter value (JSON) |
| `/reset-counter2` | POST | Reset Device 2 counter |

## 📊 Database Tables

**Device 1 Tables:**
- `faculty` - Faculty registrations
- `scan_record` - Scan history
- `meal_counter` - Current count

**Device 2 Tables (New):**
- `faculty2` - Faculty registrations
- `scan_record2` - Scan history
- `meal_counter2` - Current count

## 🎤 Voice Features

### Automatic Announcements:
1. **On Scan:** "Meal served to [Faculty Name]"
2. **Counter Update:** "Meal served. Total: [X]" or "[X] meals. Total: [Y]"
3. **System Status:** "Counter connected", "Counter reset to zero"

### Text-to-Speech Fallback Chain:
1. Browser Web Speech API (JavaScript)
2. Server-side espeak (Raspberry Pi Linux)
3. Server-side festival (Backup)
4. Visual alerts only (Ultimate fallback)

## 🖼️ UI Features

### Pop-up Notification:
- **Appearance:** Green box with checkmark + faculty name
- **Animation:** Smooth scale-in and scale-out
- **Duration:** 3 seconds before auto-closing
- **Position:** Center of screen
- **Sound:** Accompanied by audio announcement

### Counter Display:
- **Size:** Large 100px font for visibility
- **Color Change:** Flashes green when count updates
- **Real-time Updates:** Via Socket.IO (WebSocket or polling fallback)
- **Status Indicator:** Shows connection status (green/red)

## 🔗 Socket.IO Configuration

### Device 1:
```javascript
Namespace: '/'
Connection status: "🟢 Live - Connected to Dashboard"
```

### Device 2:
```javascript
Namespace: '/device2'
Connection status: "🟢 Live - Connected to Device 2"
```

**Result:** Each device only receives its own events - complete isolation

## 🧪 Testing Checklist

- [ ] Open `/counter` page and enable audio
- [ ] Have faculty scan on Device 1
- [ ] Verify green pop-up appears with faculty name
- [ ] Verify audio announcement plays
- [ ] Verify counter increments
- [ ] Open `/counter2` page in new tab/window
- [ ] Have different faculty scan on Device 2
- [ ] Verify Device 2 counter increments independently
- [ ] Verify Device 1 counter unchanged after Device 2 scan
- [ ] Verify Device 2 has separate pop-up/voice
- [ ] Test reset button on both devices
- [ ] Test voice with audio disabled (visual alert appears)

## 🚀 Deployment Notes

1. **Database Migration:** Run Flask to create new tables (Faculty2, ScanRecord2, MealCounter2)
2. **No Breaking Changes:** Existing Device 1 data and endpoints unchanged
3. **Socket.IO:** Ensure `/device2` namespace is properly configured
4. **QR Code Generation:** Generate separate QR codes for `/scan` and `/scan2` endpoints
5. **Audio System:** Both devices use same `/api/speak` endpoint

## 📝 Key Technical Details

### Cookie Separation:
```
Device 1: Set-Cookie: faculty_id=<uuid>
Device 2: Set-Cookie: faculty_id_2=<uuid>
```

### Event Emission:
```python
# Device 1
socketio.emit('new_scan', data, namespace='/')

# Device 2
socketio.emit('new_scan', data, namespace='/device2')
```

### Frontend Socket Connection:
```javascript
// Device 2
socket = io({
    namespace: '/device2',
    path: '/auto_canteen/socket.io/'
});
```

## 🛠️ Troubleshooting

**Pop-up not showing:**
- Check browser console for JavaScript errors
- Ensure Socket.IO is connected
- Verify `/api/speak` endpoint is responding

**Audio not playing:**
- Click "Enable Audio" button first (browser requirement)
- Check browser speaker volume
- Verify espeak is installed on Raspberry Pi: `sudo apt-get install espeak`

**Counter not updating:**
- Check Socket.IO namespace connection
- Verify browser's network connection
- Check server logs for errors

**Device 2 affecting Device 1:**
- Clear browser cookies and reload
- Verify using different browser tabs/windows
- Check that cookies are using `faculty_id` vs `faculty_id_2`

## 📖 File References

**Modified Files:**
- [app.py](./app.py) - Backend logic for both devices
- [counter.html](./templates/counter.html) - Pop-up & voice features added

**New Files:**
- [counter2.html](./templates/counter2.html) - Device 2 counter interface
- [IMPLEMENTATION_DUAL_DEVICE.md](./IMPLEMENTATION_DUAL_DEVICE.md) - Detailed implementation docs

## ✅ Feature Completion

| Feature | Status | Details |
|---------|--------|---------|
| Pop-up on scan | ✅ | Green popup with faculty name |
| Voice announcement | ✅ | Speaks faculty name on scan |
| Device 2 counter | ✅ | Separate device with independent count |
| Separate endpoints | ✅ | /register2, /scan2, /counter2, etc. |
| Data isolation | ✅ | Faculty2, ScanRecord2, MealCounter2 tables |
| Socket isolation | ✅ | /device2 namespace |
| Cookie isolation | ✅ | faculty_id_2 for Device 2 |

All requirements completed successfully! 🎉
