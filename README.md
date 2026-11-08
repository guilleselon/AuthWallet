# Web3 Auth & Relay — MVP

> ⚠️ **This is a learning MVP, not a production product.**
>
> It contains two independent backend services. **The Auth Service is fully
> working and deployed. The Relay Service is built, tested, and ready for
> integration, but is not currently wired into the demo flow** due to external
> restrictions (see "Why the Relay exists" below). It works end-to-end in the
> demo on desktop and mobile browsers, but has documented limitations that make
> it unsafe to run in production as-is. Use it as a reference implementation to
> learn EIP-4361 (SIWE) and the WalletConnect IRN relay architecture, then build
> your own production version on top of what works here.

A monorepo containing two backend services and a demo DApp:

1. **Auth Service** — **Status: ✅ Deployed & Working.** Signs users in via
   Sign-In with Ethereum (EIP-4361), issues sessions, and manages nonces.
   This is the "product" part of the repo: a working, useful authentication
   service you can fork and use today.
2. **Relay Service** — **Status: 🏗️ Built & Tested, not yet integrated.**
   A WebSocket message broker implementing a subset of the WalletConnect v2
   IRN protocol. It is a complete, standalone piece of infrastructure that
   demonstrates protocol implementation, but it is **not** called by the
   demo DApp yet. See "Why the Relay exists" for the honest reason.
3. **Demo DApp** — A FastHTML frontend to test the Auth Service flow locally
   and in the cloud. It exercises the Auth Service only; the Relay is not in
   this loop.

---

## Why the Relay exists (honest section)

The original goal of this repository was to build a **WalletConnect relay
from scratch** to understand how WalletConnect works under the hood. This is
why the Relay Service exists: full JSON-RPC `irn_*` handlers, pub/sub,
TTL-based message persistence, and WebSocket connection management — all
written from scratch, not wrapped around the official SDK.

**What went wrong:** WalletConnect Cloud blocks registration from certain
regions (including Cuba). The official `@walletconnect/sign-client` SDK
requires a valid `projectId` from their cloud, and cannot be configured to
use a self-hosted relay without it, because the SDK validates the
`projectId` against their backend during initialization.

**What I did instead:** rather than abandon the project, I pivoted and built
a **fully working, deployable SIWE authentication service** on top of the
same hexagonal architecture, with the same rigor: ~120 tests, Redis
persistence, dual session management (cookies for desktop, tokens for
mobile), and a working demo deployed on free-tier PaaS.

**Why the Relay is still in the repo:** it is not dead code. It is:

- A complete, tested implementation of a hard problem (~150 tests, real
  WebSocket integration tests, Redis pub/sub).
- A reference for anyone who wants to build a self-hosted WalletConnect
  relay without depending on Reown's cloud.
- The foundation for the next phase of this project, which is to integrate
  it with a WalletConnect client once a valid `projectId` can be obtained
  (through a collaborator outside the restricted region, or once the
  upcoming decentralized WalletConnect Network becomes available).

The Relay does not affect the Auth Service's correctness. You can clone this
repo, use only the Auth Service, and never touch the Relay. Both are
independent.

---

## What the Auth Service does

Without this service, a DApp has no secure way to know *who* is connected
without relying on centralized identity providers or insecure wallet
injection hacks.

With **SIWE (EIP-4361)**, the user signs a structured message containing a
nonce, domain, and chain ID. This service validates the signature, consumes
the nonce (anti-replay), and issues a session (HttpOnly Cookie for desktop,
Bearer Token for mobile). It solves the "Connect Wallet" vs. "Authenticate
Wallet" problem.

---

## How the Auth Flow works

```

User (MetaMask / Trust Wallet)
│  1. Request nonce
│  POST /auth/nonce { address }
▼
Auth Service  →  IssueNonceUseCase
├─ generate secure nonce (128-bit)
├─ store nonce in Redis (TTL 5 mins)
└─ build EIP-4361 message (domain, chain_id, nonce)
│  200 { message, nonce }
▼
User (Wallet)
│  2. personal_sign(message)
│  3. POST /auth/verify { message, signature }
▼
Auth Service  →  VerifyLoginUseCase
├─ parse message, check domain & chain_id
├─ consume nonce (atomic Lua script for Redis 2.6+ compat)
├─ recover signer address from signature
├─ create session
└─ issue Cookie + Bearer Token
│  200 { address, token }
▼
User (DApp) saves token in localStorage (mobile) or relies on Cookie (desktop).

```

---

## Architecture

Hexagonal (Ports & Adapters). Dependencies point inward, always.

```

auth-service/     FastAPI routes                  (frameworks)
│
auth-service/     Redis, eth-account, system      (adapters)
│
auth-service/     IssueNonce, VerifyLogin         (use cases)
│
auth-service/     Entities, VOs, ports, services  (business rules)

```

| Layer | Responsibility | Knows about |
|---|---|---|
| `domain/` | Entities (`Session`), value objects (`Address`, `Nonce`), ports (`Protocol`s), pure SIWE parsing | Nothing external |
| `ports/` | `NonceStore`, `SessionStore`, `SiweService`, `Clock` | `domain/` only |
| `service/` | Use cases orchestrating the ports | `domain/`, `ports/` |
| `adapters/` | `RedisNonceStore`, `SigninWithEthereumSiweService`, FastAPI routes, WebSocket handlers | `domain/`, `ports/`, third-party libs |
| `main.py` | Composition root (wires everything) | All of the above |

The only file that knows concrete implementations is `main.py` in each
service. Swapping In-Memory for Redis is a **one-line change** in the
composition root.

---

## Project layout

```

.
├── auth-service/              # ✅ SIWE authentication (FastAPI) — DEPLOYED
│   ├── Dockerfile             # Container definition for cloud deploy
│   ├── requirements.txt       # Python dependencies
│   ├── src/auth_service/
│   │   ├── domain/            # Pure logic, no I/O
│   │   ├── ports/             # Interfaces (Protocols)
│   │   ├── service/           # Use cases
│   │   ├── adapters/          # Redis, EIP-4361, FastAPI
│   │   └── main.py            # Composition root
│   └── tests/                 # ~120 tests
│
├── relay/                     # 🏗️ WalletConnect IRN subset — NOT INTEGRATED
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── src/relay/
│   │   ├── domain/            # Pure logic, JSON-RPC framing
│   │   ├── ports/             # Interfaces (Protocols)
│   │   ├── service/           # Message routing, Pub/Sub logic
│   │   ├── adapters/          # Redis PubSub, WebSockets, JWT
│   │   └── main.py            # Composition root
│   └── tests/                 # ~150 tests
│
├── examples/
│   └── demo-dapp/             # FastHTML frontend (uses Auth Service only)
│       ├── Dockerfile
│       ├── requirements.txt
│       └── src/demo_dapp/
│
├── docs/
│   ├── architecture.md        # ADRs and hexagonal rationale
│   ├── auth-flow.md           # EIP-4361 sequence diagram
│   └── relay-protocol.md      # IRN JSON-RPC methods (reference)
│
└── README.md

```

---

## Quickstart (Local Dev)

### 1. Prerequisites
- Python **3.11+**
- **Docker** (for local Redis)

### 2. Start Redis
```bash
docker run -d --name redis-local -p 6379:6379 redis:7-alpine
```

3. Install & Run Auth Service

```bash
cd auth-service
pip install -e ".[dev,redis,siwe]"

export AUTH_DOMAIN="localhost"
export AUTH_URI="http://localhost:8080"
export AUTH_CHAIN_ID=56
export AUTH_COOKIE_SECURE=false
export AUTH_CORS_ORIGINS="http://localhost:3000"
export AUTH_STORE=redis
export REDIS_URL="redis://localhost:6379/0"
export AUTH_COOKIE_SECRET="generate-a-64-char-random-string-here"

uvicorn src.auth_service.main:app --host 0.0.0.0 --port 8080
```

4. Install & Run Demo DApp

Open a new terminal:

```bash
cd examples/demo-dapp
pip install -e .

export AUTH_URL="http://localhost:8080"
uvicorn src.demo_dapp.main:app --host 0.0.0.0 --port 3000
```

Open http://localhost:3000. Connect MetaMask, sign the message, and test
the session.

5. (Optional) Run the Relay standalone

The Relay is not used by the demo DApp, but you can run it standalone and
test it with websocat or a WebSocket client:

```bash
cd relay
pip install -e ".[dev,redis,jwt]"

export RELAY_TOKENS="dev-token:proj-1"
export RELAY_AUTH=jwt
export RELAY_HOST=0.0.0.0
export RELAY_PORT=8765

uvicorn src.relay.main:app --host 0.0.0.0 --port 8765
```

See docs/relay-protocol.md for the JSON-RPC methods it implements.

---

Docker Deployment (Cloud)

Both services are containerized. The Dockerfile and requirements.txt are located at the root of each service directory.

To build the images locally:

```bash
# Build Auth Service
docker build -t my-auth-service ./auth-service

# Build Demo DApp
docker build -t my-demo-dapp ./examples/demo-dapp
```

(Note: When deploying to platforms like Orkestr or Hostless, set the "Root Directory" or "Build Context" to auth-service or examples/demo-dapp respectively.)

---

Testing

Both services are heavily tested.

· Auth Service: ~120 tests (Domain, Service, Adapters, E2E). No network
  required; uses fakeredis and real eth_account keypairs.
· Relay Service: ~150 tests (Domain, Protocol, WebSockets, Redis).
  Includes real WebSocket integration tests on ephemeral ports.

```bash
cd auth-service && pytest -v
cd relay        && pytest -v
```

---

Known limitations

🔴 Auth Service — Will bite you in production

1. No Rate Limiting on /auth/nonce.
   Anyone can spam the endpoint, consuming Redis space and potentially
   causing DoS. Fix: Add slowapi or an Nginx limit_req rule.
2. Mobile Cookie Blocking.
   Mobile wallets (Trust Wallet, etc.) block SameSite=None cookies. We
   mitigated this with a Bearer Token fallback (localStorage), but this
   is vulnerable to XSS if the DApp is not strictly sanitized.
3. Cold Starts (Free Tier).
   On platforms like Orkestr/Hostless, the container sleeps after 15
   minutes. The first fetch from MetaMask will timeout (Failed to
      fetch). Fix: Ping /health every 5 minutes via UptimeRobot, or use
   a paid tier.
4. No EIP-1271 (Smart Contract Wallets).
   The SiweService adapter uses standard ECDSA recovery. It cannot verify
   signatures from Safe (Gnosis) or other smart contract wallets. Fix:
   Add a Web3 provider call to isValidSignature if the address is a
   contract.

🔴 Relay Service — Will bite you in production

1. JWT signature verification is bypassed.
   JwtTokenValidator decodes the JWT but does not verify its
   signature. This was a deliberate MVP choice because WalletConnect Cloud
   blocks the region, so we cannot obtain a valid projectId signed by
   Reown. Anyone can forge a JWT and connect. Fix: Verify against
   Reown's public keys, or replace with a self-hosted auth scheme.
2. No Rate Limiting on WebSocket connects.
   Trivial DoS vector. Fix: Nginx limit_conn + per-IP caps.
3. Single-instance only.
   InMemoryConnectionManager limits the relay to one process. Redis
   Pub/Sub supports cross-instance routing, but connection tracking is
   local. Fix: Move connection state to Redis or use a sticky LB with
   consistent hashing.

🟡 Paper cuts, not blockers

· MetaMask Android Deep Link bug.
  link.metamask.io opens a blank white screen on Android. We mitigated
  with metamask.app.link/dapp/, but it still fails occasionally on older
  OS versions.
· Relay Redis GETDEL compatibility.
  Replaced with a Lua script for Redis 2.6+ compat. Slightly slower but
  portable.
· No WSS in Local Dev.
  Relay runs over ws://. In production, put it behind Nginx with TLS.
· Relay message TTL.
  Messages retained in Redis for max 7 days. Longer offline periods lose
  messages.

---

Path to production

In priority order:

1. Auth Service: Add rate limiting on /auth/nonce and /auth/verify.
2. Auth Service: Move to a paid tier (or a $5 VPS) to eliminate Cold
   Starts.
3. Auth Service: Implement EIP-1271 for Smart Contract Wallets.
4. Relay Service: Implement JWT signature verification.
5. Relay Service: Add rate limiting on WebSocket connects.
6. Full stack: Build a real frontend (React/Next.js) with proper XSS
   sanitization.
7. Full stack: Integrate the Relay with the DApp via WalletConnect (or
   WalletCast, if WalletConnect Cloud remains blocked).

---

Security notes

· Never commit your AUTH_COOKIE_SECRET. Use .env files or a secret
  manager.
· Use HTTPS in production. The Secure cookie flag requires it.
· The Relay is a blind broker. It does not read message contents, but
  it does know who is talking to whom (by IP and projectId). If privacy
  is a concern, consider using Tor or a mixnet for the Relay.
· Do not use this on Mainnet with real funds until the JWT verification
  and Rate Limiting are implemented.

---

License

MIT. It's a learning project. Fork it, learn from it, build something
better. No warranty, no support, no production readiness implied.

```
