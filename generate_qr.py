import qrcode

img = qrcode.make("http://192.168.0.102:5000/scan")
img.save("static_qr.png")