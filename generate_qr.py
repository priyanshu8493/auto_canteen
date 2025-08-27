import qrcode

img = qrcode.make("http://192.168.0.108:5000/scan")
img.save("static_qr.png")