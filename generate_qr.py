import qrcode

img = qrcode.make("http://172.20.10.5:5000/scan")
img.save("static_qr.png")