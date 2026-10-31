"""Ethereum-specific outbound adapters.

`SigninWithEthereumSiweService` is the production implementation of
the `SiweService` port. It wraps the `signinwithethereum` package
(import name: `siwe`) so that the rest of the codebase never depends
on the library directly.
"""
from .siwe_service import SigninWithEthereumSiweService

__all__ = ["SigninWithEthereumSiweService"]
