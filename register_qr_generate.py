import qrcode

img = qrcode.make("http://172.20.10.5:5000/register")

img.save("register_qr.png")