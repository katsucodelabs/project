from __future__ import annotations

import uuid
from dataclasses import dataclass
from io import BytesIO
from urllib.parse import urlencode

import aiohttp
import qrcode


@dataclass(frozen=True)
class PaymentInvoice:
    invoice: str
    amount: int
    payment_url: str
    qris_png: bytes
    qris_content: str


class PakasirClient:
    def __init__(self, slug: str, api_key: str, base_url: str) -> None:
        self.slug = slug
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _payment_url(self, invoice: str, amount: int) -> str:
        query = urlencode({"order_id": invoice, "qris_only": 1})
        return f"{self.base_url}/pay/{self.slug}/{amount}?{query}"

    @staticmethod
    def _make_qr_png(content: str) -> bytes:
        qr = qrcode.QRCode(version=None, box_size=10, border=4)
        qr.add_data(content)
        qr.make(fit=True)
        image = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    async def create_invoice(self, amount: int) -> PaymentInvoice:
        invoice = f"VIP-{uuid.uuid4().hex[:12].upper()}"
        payment_url = self._payment_url(invoice, amount)
        payload = {
            "project": self.slug,
            "order_id": invoice,
            "amount": amount,
            "api_key": self.api_key,
        }
        qris_content = payment_url
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/transactioncreate/qris",
                    json=payload,
                    timeout=20,
                ) as response:
                    if response.status < 400:
                        data = await response.json(content_type=None)
                        payment = data.get("payment") or data.get("transaction") or data
                        qris_content = str(payment.get("payment_number") or payment.get("qr_string") or payment_url)
        except (aiohttp.ClientError, TimeoutError, ValueError):
            # Fall back to a QR code for Pakasir's qris_only payment URL so Telegram
            # still receives an image instead of failing on a non-image endpoint.
            qris_content = payment_url
        return PaymentInvoice(
            invoice=invoice,
            amount=amount,
            payment_url=payment_url,
            qris_png=self._make_qr_png(qris_content),
            qris_content=qris_content,
        )

    async def is_paid(self, invoice: str, amount: int) -> bool:
        params = {"project": self.slug, "amount": amount, "order_id": invoice, "api_key": self.api_key}
        url = f"{self.base_url}/api/transactiondetail"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=20) as response:
                if response.status >= 400:
                    return False
                data = await response.json(content_type=None)
        transaction = data.get("transaction") or data.get("payment") or data
        status = str(transaction.get("status") or transaction.get("transaction_status") or "").lower()
        paid_flags = {"completed", "success", "paid", "settlement", "berhasil"}
        return status in paid_flags or bool(transaction.get("paid"))
