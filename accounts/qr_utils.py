import base64
import json
from io import BytesIO

import qrcode


def generate_invoice_qr(invoice):

    product_count = invoice.items.count()

    qr_data = {
        "invoice_number": str(invoice.invoice_number),
        "customer_name": str(invoice.customer.name),
        "invoice_date": str(invoice.invoice_date),
        "product_count": product_count,
        "total": str(invoice.total_amount),
    }

    qr_text = json.dumps(
        qr_data,
        separators=(",", ":")
    )

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=4,
    )

    qr.add_data(qr_text)
    qr.make(fit=True)

    qr_image = qr.make_image(
        fill_color="black",
        back_color="white"
    )

    buffer = BytesIO()

    qr_image.save(
        buffer,
        format="PNG"
    )

    qr_base64 = base64.b64encode(
        buffer.getvalue()
    ).decode("utf-8")

    return qr_base64