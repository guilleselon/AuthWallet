"""DApp de demo para probar SIWE con auth-service."""
from __future__ import annotations

import os

from fasthtml.common import (
    A,           # Importante para los enlaces del dropdown
    Button,
    Div,
    P,
    Script,
    Titled,
    fast_app,
)

AUTH_URL = os.environ.get("AUTH_URL", "http://localhost:8080")
app, rt = fast_app(secret_key="demo-dapp-key-not-used")

PAGE_JS = f"""
const AUTH_URL = {AUTH_URL!r};

// ─── Login Principal ─────────────────────────────────────────
async function login() {{
    const status = document.getElementById('status');
    
    // Verificamos la wallet EN EL MOMENTO DEL CLIC
    if (typeof window.ethereum === 'undefined') {{
        status.innerHTML = '<span style="color:red;"><b>⚠️ No estás dentro de una wallet.</b></span><br>' +
                           'Si estás en Chrome/Safari, por favor usa el menú <b>"Elegir Wallet ▼"</b> para abrir esta DApp dentro de tu wallet móvil.';
        return;
    }}

    try {{
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
        localStorage.setItem('auth_token', session.token);

        status.innerHTML =
            '<b style="color:green;">✅ Login correcto</b><br>' +
            'Address: <code>' + session.address + '</code><br>' +
            'Chain ID: ' + session.chain_id + '<br>' +
            'Expira: ' + new Date(session.expires_at * 1000).toLocaleString();
    }} catch (err) {{
        status.textContent = 'Error: ' + (err.message || err);
    }}
}}

// ─── Menú Desplegable de Wallets ─────────────────────────────
function openWalletMenu() {{
    document.getElementById('wallet-dropdown').classList.toggle('show');
}}

// Cerrar el menú si se hace clic fuera
window.onclick = function(event) {{
    if (!event.target.matches('.dropbtn')) {{
        const dropdowns = document.getElementsByClassName("dropdown-content");
        for (let i = 0; i < dropdowns.length; i++) {{
            if (dropdowns[i].classList.contains('show')) {{
                dropdowns[i].classList.remove('show');
            }}
        }}
    }}
}}

function redirectToWallet(wallet) {{
    const currentUrl = window.location.host + window.location.pathname;
    if (wallet === 'metamask') {{
        window.location.href = 'https://metamask.app.link/dapp/' + currentUrl;
    }} else if (wallet === 'trust') {{
        window.location.href = 'https://link.trustwallet.com/open_url?coin_id=60&url=' + encodeURIComponent(window.location.href);
    }} else if (wallet === 'coinbase') {{
        window.location.href = 'https://go.cb-w.com/dapp?cb_url=' + encodeURIComponent(window.location.href);
    }}
}}

// ─── Whoami / Logout ─────────────────────────────────────────
async function whoami() {{
    const status = document.getElementById('status');
    try {{
        const token = localStorage.getItem('auth_token');
        const headers = token ? {{ 'Authorization': `Bearer ${{token}}` }} : {{}};
        
        const r = await fetch(`${{AUTH_URL}}/auth/me`, {{ credentials: 'include', headers: headers }});
        
        if (r.status === 401) {{
            status.textContent = 'No hay sesión activa.';
            localStorage.removeItem('auth_token');
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
        await fetch(`${{AUTH_URL}}/auth/logout`, {{ method: 'POST', credentials: 'include', headers: headers }});
        localStorage.removeItem('auth_token');
        status.textContent = 'Sesión cerrada.';
    }} catch (err) {{
        status.textContent = 'Error: ' + (err.message || err);
    }}
}}
"""

STYLES = """
<style>
.dropdown { position: relative; display: inline-block; margin-left: 8px; }
.dropbtn { background-color: #e0e0e0; color: black; padding: 8px 16px; font-size: 14px; border: 1px solid #999; cursor: pointer; border-radius: 4px; font-weight: bold;}
.dropdown-content { display: none; position: absolute; background-color: #f9f9f9; min-width: 180px; box-shadow: 0px 8px 16px 0px rgba(0,0,0,0.2); z-index: 1; right: 0; border-radius: 4px; overflow: hidden;}
.dropdown-content a { color: black; padding: 12px 16px; text-decoration: none; display: block; cursor: pointer; font-family: sans-serif;}
.dropdown-content a:hover { background-color: #ddd; }
.show { display: block; }
</style>
"""

@rt("/")
def get():
    return Titled(
        "Demo DApp — SIWE",
        Script(STYLES),
        P("Autenticación con Sign-In with Ethereum (EIP-4361)."),

        Div(
            Button("Login con wallet", onclick="login()"),
            Button("¿Quién soy?", onclick="whoami()", style="margin-left:8px;"),
            Button("Logout", onclick="logout()", style="margin-left:8px;"),
            
            # Menú Desplegable
            Div(
                Button("Elegir Wallet ▼", onclick="openWalletMenu()", cls="dropbtn"),
                Div(
                    A("Abrir en MetaMask", onclick="redirectToWallet('metamask')"),
                    A("Abrir en Trust Wallet", onclick="redirectToWallet('trust')"),
                    A("Abrir en Coinbase", onclick="redirectToWallet('coinbase')"),
                    id="wallet-dropdown", cls="dropdown-content"
                ),
                cls="dropdown"
            ),
            style="margin-top:16px;",
        ),

        P(id="status", style="font-family:monospace; margin-top:24px; white-space:pre-line;"),
        Script(PAGE_JS),
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("demo_dapp.main:app", host="0.0.0.0", port=3000, reload=True)
