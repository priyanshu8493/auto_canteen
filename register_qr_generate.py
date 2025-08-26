import qrcode

img = qrcode.make("localhost:5000/register")

img.save("register_qr.png")