import qrcode

img = qrcode.make("http://192.168.0.108:5000/register")

img.save("register_qr.png")