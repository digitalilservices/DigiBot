# services/cryptobot.py
from __future__ import annotations

import aiohttp
from typing import Any, Dict, Optional


class CryptoBotError(Exception):
    pass


class CryptoBotAPI:
    """
    CryptoBot Pay API wrapper (async).
    Docs: https://help.crypt.bot/crypto-pay-api (официальная документация)
    """

    def __init__(self, token: str, base_url: str = "https://pay.crypt.bot/api"):
        self.token = token
        self.base_url = base_url.rstrip("/")

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "Crypto-Pay-API-Token": self.token,
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, path: str, params: Optional[dict] = None, json: Optional[dict] = None) -> dict:
        url = f"{self.base_url}/{path.lstrip('/')}"
        timeout = aiohttp.ClientTimeout(total=20)

        async with aiohttp.ClientSession(timeout=timeout, headers=self._headers) as session:
            async with session.request(method=method.upper(), url=url, params=params, json=json) as resp:
                try:
                    data = await resp.json(content_type=None)
                except Exception:
                    text = await resp.text()
                    raise CryptoBotError(f"CryptoBot response is not JSON. HTTP {resp.status}. Body: {text[:500]}")

                if resp.status >= 400:
                    raise CryptoBotError(f"CryptoBot HTTP error {resp.status}: {data}")

                # CryptoBot usually: {"ok":true,"result":{...}}
                ok = data.get("ok", False)
                if not ok:
                    raise CryptoBotError(f"CryptoBot API error: {data}")

                return data.get("result", {})

    async def create_check(self, asset: str, amount: float):
        """
        Созение чека через CryptoBot API
        """
        payload = {
            "asset": asset,
            "amount": amount
        }

        data = await self._post("createCheck", payload)

        if not data.get("ok"):
            raise Exception(f"CryptoBot error: {data}")

        return data["result"]

    async def create_invoice(self, amount: float, asset: str = "USDT", description: str = "Invoice") -> Dict[str, Any]:
        """
        Returns: {invoice_id, pay_url, status, ...}
        """
        payload = {
            "asset": asset,
            "amount": str(amount),
            "description": description,
        }
        result = await self._request("POST", "/createInvoice", json=payload)
        if "invoice_id" not in result or "pay_url" not in result:
            raise CryptoBotError(f"Unexpected createInvoice result: {result}")
        return result

    async def get_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """
        CryptoBot method is usually getInvoices with invoice_ids.
        We'll request single invoice and return it.
        """
        params = {
            "invoice_ids": invoice_id
        }
        result = await self._request("GET", "/getInvoices", params=params)

        items = result.get("items") if isinstance(result, dict) else None
        if not items:
            # sometimes result itself might be list-like
            if isinstance(result, list) and result:
                return result[0]
            raise CryptoBotError(f"Invoice not found: {invoice_id}")

        return items[0]
