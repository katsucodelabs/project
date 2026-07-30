from __future__ import annotations

import uuid
from dataclasses import dataclass
from urllib.parse import urlencode

import aiohttp


@dataclass(frozen=True)
class PaymentInvoice:
    invoice: str
    amount: int
    payment_url: str
    qris_url: str


class PakasirClient:
    def __init__(self, slug: str, api_key: str, base_url: str) -> None:
        self.slug = slug
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def create_invoice(self, amount: int) -> PaymentInvoice:
        invoice = f"VIP-{uuid.uuid4().hex[:12].upper()}"
        query = urlencode({"amount": amount, "order_id": invoice})
        payment_url = f"{self.base_url}/pay/{self.slug}?{query}"
        # Pakasir exposes QRIS images from the same payment route in many integrations.
        # Keep this configurable through the base URL and always include the exact invoice.
        qris_url = f"{self.base_url}/qris/{self.slug}?{query}"
        return PaymentInvoice(invoice=invoice, amount=amount, payment_url=payment_url, qris_url=qris_url)

    async def is_paid(self, invoice: str, amount: int) -> bool:
        params = {"project": self.slug, "amount": amount, "order_id": invoice, "api_key": self.api_key}
        url = f"{self.base_url}/api/transactiondetail"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=20) as response:
                if response.status >= 400:
                    return False
                data = await response.json(content_type=None)
        status = str(data.get("status") or data.get("transaction_status") or "").lower()
        paid_flags = {"completed", "success", "paid", "settlement", "berhasil"}
        return status in paid_flags or bool(data.get("paid"))
