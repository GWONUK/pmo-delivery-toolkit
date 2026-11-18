"""Bounded publication checks. Passing is not a complete secret-detection guarantee."""
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SKIP = {'.git', '__pycache__', '.venv', 'venv', 'artifacts'}
PATTERNS = {
    'private_key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'cloud_access_key': re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'github_token': re.compile(r'\bgh[pousr]_[A-Za-z0-9]{30,}\b'),
    'home_path': re.compile(r'[A-Z]:[\\/]+Users[\\/]+[^\s"\']+', re.I),
    'korean_mobile': re.compile(r'\b01[016789][- ]\d{3,4}[- ]\d{4}\b'),
    'email': re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'),
}
PRIVATE = tuple(ipaddress.ip_network(x) for x in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16'))


def main():
    errors, checked = [], []
    for file in sorted(ROOT.rglob('*')):
        rel = file.relative_to(ROOT)
        if any(part in SKIP for part in rel.parts) or not file.is_file():
            continue
        if file.is_symlink():
            errors.append((str(rel), 'symlink'))
            continue
        if file.name == '.env' or file.suffix.lower() in ('.pem','.key','.p12','.pfx','.kubeconfig'):
            errors.append((str(rel), 'credential_file_type'))
        raw = file.read_bytes()
        text = raw.decode('utf-8')
        checked.append(str(rel))
        # This scanner contains the network ranges that it rejects elsewhere.
        if file == Path(__file__).resolve():
            continue
        for label, pattern in PATTERNS.items():
            for match in pattern.finditer(text):
                if label == 'email' and (match.group().endswith('@example.invalid')
                        or match.group().split('@')[-1] in ('example.com', 'api.example.com')):
                    continue
                errors.append((str(rel), label))
        for match in re.finditer(r'(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])', text):
            try:
                addr = ipaddress.ip_address(match.group())
            except ValueError:
                continue
            if any(addr in subnet for subnet in PRIVATE):
                errors.append((str(rel), 'private_ipv4'))
    manifest = json.loads((ROOT / 'docs/source-provenance.json').read_text(encoding='utf-8'))
    for entry in manifest:
        actual = hashlib.sha256((ROOT / entry['path']).read_bytes()).hexdigest()
        if actual != entry['public_sha256']:
            errors.append((entry['path'], 'provenance_hash_mismatch'))
    print(json.dumps({'checked_files': len(checked), 'patterns_and_provenance_passed': not errors,
                      'findings': sorted(set(errors))}, ensure_ascii=False, indent=2))
    return bool(errors)


if __name__ == '__main__':
    sys.exit(main())
