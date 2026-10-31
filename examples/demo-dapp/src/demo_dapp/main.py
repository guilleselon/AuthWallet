"""DApp de demo para probar SIWE con auth-service."""
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

app, rt = fast_app(secret_key="demo-dapp-session-key-not-used-because-we-use-auth-service")


PAGE_JS = f"""
const AUTH_URL = {AUTH_URL!r};

const isMobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
const hasInjectedWallet = typeof window.ethereum !== 'undefined';

// ─── Login ───────────────────────────────────────────────────
async function login() {{
    const status = document.getElementById('status');
    try {{
        if (!window.ethereum) {{
            status.textContent = 'No hay wallet inyectada.';
            return;
        }}

        status.textContent = 'Conectando MetaMask...';
        const accounts = await window.ethereum.request({{ method: 'eth_requestAccounts' }});
        const address = accounts[0];

        status.textContent = 'Pidiendo nonce...';
        const nonceResp = await fetch(`${{AUTH_URL}}/auth/nonce`, {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            credentials: 'include',
            body: JSON.stringify({{ address }}),
        }});
        if (!nonceResp.ok) throw new Error(`nonce ${{nonceResp.status}}: ${{await nonceResp.text()}}`);
        const {{ message }} = await nonceResp.json();

        status.textContent = 'Firma el mensaje en tu wallet...';
        const signature = await window.ethereum.request({{
            method: 'personal_sign',
            params: [message, address],
        }});

        status.textContent = 'Verificando...';
        const verifyResp = await fetch(`${{AUTH_URL}}/auth/verify`, {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            credentials: 'include',
            body: JSON.stringify({{ message, signature }}),
        }});
        if (!verifyResp.ok) throw new Error(`verify ${{verifyResp.status}}: ${{await verifyResp.text()}}`);
        const session = await verifyResp.json();

        status.innerHTML =
            '<b>✅ Login correcto</b><br>' +
            'Address: <code>' + session.address + '</code><br>' +
            'Chain ID: ' + session.chain_id + '<br>' +
            'Expira: ' + new Date(session.expires_at * 1000).toLocaleString();
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
            status.textContent = 'No hay sesión activa.';
            return;
        }}
        const s = await r.json();
        status.innerHTML = '<b>Sesión activa:</b><br>Address: <code>' + s.address + '</code>';
    }} catch (err) {{
        status.textContent = 'Error: ' + (err.message || err);
    }}
}}

async function logout() {{
    const status = document.getElementById('status');
    try {{
        await fetch(`${{AUTH_URL}}/auth/logout`, {{ method: 'POST', credentials: 'include' }});
        status.textContent = 'Sesión cerrada.';
    }} catch (err) {{
        status.textContent = 'Error: ' + (err.message || err);
    }}
}}

// ─── Mostrar botones (sin DOMContentLoaded) ──────────────────
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
        P("Autenticación con Sign-In with Ethereum (EIP-4361)."),

        # Botones de Login (ocultos por defecto, se muestran si hay wallet)
        Div(
            Button("Login con wallet", onclick="login()"),
            Button("¿Quién soy?", onclick="whoami()", style="margin-left:8px;"),
            Button("Logout", onclick="logout()", style="margin-left:8px;"),
            id="wallet-actions",
            style="display:none; margin-top:16px;",
        ),

        # Botones de Deep Link (visibles por defecto, se ocultan si hay wallet)
        Div(
            P("Abre esta DApp en el navegador de tu wallet:"),
            Button("Abrir en MetaMask", onclick="openInMetaMask()"),
            Button("Abrir en Trust", onclick="openInTrust()", style="margin-left:8px;"),
            Button("Abrir en Coinbase", onclick="openInCoinbase()", style="margin-left:8px;"),
            id="deep-links",
            style="display:block; margin-top:16px;",
        ),

        P(
            "Si estás en escritorio, instala MetaMask o abre esta URL en tu móvil.",
            id="desktop-hint",
            style="display:none; color:#a00; margin-top:12px;",
        ),

        P(id="status", style="font-family:monospace; margin-top:24px; white-space:pre-line;"),
        Script(PAGE_JS),
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("demo_dapp.main:app", host="0.0.0.0", port=3000, reload=True)
