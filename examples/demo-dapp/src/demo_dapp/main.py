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

# Forzamos secret_key para evitar el error de sistema de archivos de solo lectura en Docker
app, rt = fast_app(secret_key="demo-dapp-key-not-used")

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

        status.textContent = 'Conectando wallet...';
        const accounts = await window.ethereum.request({{ method: 'eth_requestAccounts' }});
        const address = accounts[0];

        status.textContent = 'Pidiendo nonce...';
        const nonceResp = await fetch(`${{AUTH_URL}}/auth/nonce`, {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
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
            body: JSON.stringify({{ message, signature }}),
        }});
        if (!verifyResp.ok) throw new Error(`verify ${{verifyResp.status}}: ${{await verifyResp.text()}}`);
        
        const session = await verifyResp.json();
        
        // Guardamos el token en localStorage
        localStorage.setItem('auth_token', session.token);

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
    // Formato correcto para evitar pantalla en blanco en Android
    const currentUrl = window.location.host + window.location.pathname;
    window.location.href = 'https://metamask.app.link/dapp/' + currentUrl;
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
        const token = localStorage.getItem('auth_token');
        const headers = token ? {{ 'Authorization': `Bearer ${{token}}` }} : {{}};
        
        const r = await fetch(`${{AUTH_URL}}/auth/me`, {{ 
            credentials: 'include',
            headers: headers 
        }});
        
        if (r.status === 401) {{
            status.textContent = 'No hay sesión activa.';
            localStorage.removeItem('auth_token'); // Limpiamos token inválido
            return;
        }}
        if (!r.ok) throw new Error(`me ${{r.status}}: ${{await r.text()}}`);
        
        const s = await r.json();
        status.innerHTML =
            '<b>Sesión activa:</b><br>' +
            'Address: <code>' + s.address + '</code><br>' +
            'Expira: ' + new Date(s.expires_at * 1000).toLocaleString();
    }} catch (err) {{
        status.textContent = 'Error: ' + (err.message || err);
    }}
}}

async function logout() {{
    const status = document.getElementById('status');
    try {{
        const token = localStorage.getItem('auth_token');
        const headers = token ? {{ 'Authorization': `Bearer ${{token}}` }} : {{}};

        await fetch(`${{AUTH_URL}}/auth/logout`, {{
            method: 'POST', 
            credentials: 'include',
            headers: headers
        }});
        
        localStorage.removeItem('auth_token');
        status.textContent = 'Sesión cerrada.';
    }} catch (err) {{
        status.textContent = 'Error: ' + (err.message || err);
    }}
}}

// ─── Mostrar botones ─────────────────────────────────────────
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

        Div(
            Button("Login con wallet", onclick="login()"),
            Button("¿Quién soy?", onclick="whoami()", style="margin-left:8px;"),
            Button("Logout", onclick="logout()", style="margin-left:8px;"),
            id="wallet-actions",
            style="display:none; margin-top:16px;",
        ),

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
