#!/usr/bin/env python3
"""Install a narrowly scoped private AP configuration from an Actions secret."""
import base64
import io
import os
from pathlib import Path
import sys
import tarfile

root = Path(sys.argv[1]).resolve()
payload = os.environ.get('CMCC_PRIVATE_CONFIG_B64', '')
if not payload:
    raise SystemExit('Missing private configuration secret')
allowed = {'etc/config/ddnsto', 'etc/config/zerotier'}
with tarfile.open(fileobj=io.BytesIO(base64.b64decode(payload, validate=True)), mode='r:gz') as archive:
    members = archive.getmembers()
    if len(members) != 2 or {m.name for m in members} != allowed:
        raise SystemExit('Unexpected private configuration archive contents')
    if any(not m.isfile() or m.size > 65536 for m in members):
        raise SystemExit('Invalid private configuration member')
    for member in members:
        target = root / member.name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(archive.extractfile(member).read())
        target.chmod(0o600)
# The backed-up UCI configuration uses this persistent path and contains
# the node identity; the init script populates identity.secret on first boot.
(root / 'etc/zerotier').mkdir(parents=True, exist_ok=True)
(root / 'etc/zerotier').chmod(0o700)
print('Private DDNSTO and ZeroTier configuration installed; values withheld')
