import base64
import io

import qrcode
from django import template

register = template.Library()


@register.filter
def qrcode_inline(value):
    qr = qrcode.QRCode(
        version=None, box_size=2, error_correction=qrcode.constants.ERROR_CORRECT_Q
    )
    qr.add_data(value)
    qr.make(fit=True)
    img = qr.make_image()
    with io.BytesIO() as output:
        img.save(output, format="PNG")
        return "data:image/png;base64,{}".format(
            base64.b64encode(output.getvalue()).decode("us-ascii")
        )
