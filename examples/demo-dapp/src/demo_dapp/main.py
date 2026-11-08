"""Demo DApp to test SIWE with auth-service."""
from __future__ import annotations

import os

from fasthtml.common import (
    Button,
    Div,
    P,
    Script,
    Titled,
    fast_app,
)

AUTH_URL = os.environ.get("AUTH_URL", "http://localhost:8080")

app, rt = fast_app()


PAGE_JS = f"""
const AUTH_URL = {AUTH_URL!r};

const isMobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
const hasInjectedWallet = typeof window.ethereum !== 'undefined';

// ─── Login ───────────────────────────────────────────────────
async function login() {{
    const status = document.getElementById('status');
    try {{
        if (!window.ethereum) {{
            status.textContent = 'No injected wallet.';
            return;
        }}

        status.textContent = 'Connecting to MetaMask...';
        const accounts = await window.ethereum.request({{ method: 'eth_requestAccounts' }});
        const address = accounts[0];

        status.textContent = 'Requesting nonce...';
        const nonceResp = await fetch(`${{AUTH_URL}}/auth/nonce`, {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            credentials: 'include',
            body: JSON.stringify({{ address }}),
        }});
        if (!nonceResp.ok) throw new Error(`nonce ${{nonceResp.status}}: ${{await nonceResp.text()}}`);
        const {{ message }} = await nonceResp.json();

        status.textContent = 'Sign the message in your wallet...';
        const signature = await window.ethereum.request({{
            method: 'personal_sign',
            params: [message, address],
        }});

        status.textContent = 'Verifying...';
        const verifyResp = await fetch(`${{AUTH_URL}}/auth/verify`, {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            credentials: 'include',
            body: JSON.stringify({{ message, signature }}),
        }});
        if (!verifyResp.ok) throw new Error(`verify ${{verifyResp.status}}: ${{await verifyResp.text()}}`);
        const session = await verifyResp.json();

        status.innerHTML =
            '<b>✅ Login successful</b><br>' +
            'Address: <code>' + session.address + '</code><br>' +
            'Chain ID: ' + session.chain_id + '<br>' +
            'Expires: ' + new Date(session.expires_at * 1000).toLocaleString();
    }} catch (err) {{
        status.textContent = 'Error: ' + (err.message || err);
    }}
}}

// ─── Deep links ──────────────────────────────────────────────
function openInMetaMask() {{
    window.location.href = 'https://link.metamask.io/dapp/' + encodeURIComponent(window.location.href);
}}

function openInTrust() {{
    window.location.href = 'https://link.trustwallet.com/open_url?coin_id=60&url=' + encodeURIComponent(window.location.href);
}}

function openInCoinbase() {{
    window.location.href = 'https://go.cb-w.com/dapp?cb_url=' + encodeURIComponent(window.location.href);
}}

// ─── Whoami / Logout ─────────────────────────────────────────
async function whoami() {{
    const status = document.getElementById('status');
    try {{
        const r = await fetch(`${{AUTH_URL}}/auth/me`, {{ credentials: 'include' }});
        if (r.status === 401) {{
            status.textContent = 'No active session.';
            return;
        }}
        const s = await r.json();
        status.innerHTML = '<b>Active session:</b><br>Address: <code>' + s.address + '</code>';
    }} catch (err) {{
        status.textContent = 'Error: ' + (err.message || err);
    }}
}}

async function logout() {{
    const status = document.getElementById('status');
    try {{
        await fetch(`${{AUTH_URL}}/auth/logout`, {{ method: 'POST', credentials: 'include' }});
        status.textContent = 'Logged out.';
    }} catch (err) {{
        status.textContent = 'Error: ' + (err.message || err);
    }}
}}

// ─── Show buttons (without DOMContentLoaded) ─────────────────
if (hasInjectedWallet) {{
    document.getElementById('wallet-actions').style.display = 'block';
    document.getElementById('deep-links').style.display = 'none';
}} else {{
    document.getElementById('wallet-actions').style.display = 'none';
    document.getElementById('deep-links').style.display = 'block';
    if (!isMobile) {{
        document.getElementById('desktop-hint').style.display = 'block';
    }}
}}
"""


@rt("/")
def get():
    return Titled(
        "Demo DApp — SIWE",
        P("Authentication with Sign-In with Ethereum (EIP-4361)."),

        # Login buttons (hidden by default, shown if a wallet is present)
        Div(
            Button("Login with wallet", onclick="login()"),
            Button("Who am I?", onclick="whoami()", style="margin-left:8px;"),
            Button("Logout", onclick="logout()", style="margin-left:8px;"),
            id="wallet-actions",
            style="display:none; margin-top:16px;",
        ),

        # Deep Link buttons (visible by default, hidden if a wallet is present)
        Div(
            P("Open this DApp in your wallet's browser:"),
            Button("Open in MetaMask", onclick="openInMetaMask()"),
            Button("Open in Trust", onclick="openInTrust()", style="margin-left:8px;"),
            Button("Open in Coinbase", onclick="openInCoinbase()", style="margin-left:8px;"),
            id="deep-links",
            style="display:block; margin-top:16px;",
        ),

        P(
            "If you're on desktop, install MetaMask or open this URL on your mobile.",
            id="desktop-hint",
            style="display:none; color:#a00; margin-top:12px;",
        ),

        P(id="status", style="font-family:monospace; margin-top:24px; white-space:pre-line;"),
        Script(PAGE_JS),
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("demo_dapp.main:app", host="0.0.0.0", port=3000, reload=True)
