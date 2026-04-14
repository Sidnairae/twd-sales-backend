"""
supabase_client.py — kept for backward compatibility only.

New code should import directly from app.lib.clients:
    from app.lib.clients import get_admin_client, get_anon_client
"""

from app.lib.clients import get_admin_client, get_anon_client

__all__ = ["get_admin_client", "get_anon_client"]
