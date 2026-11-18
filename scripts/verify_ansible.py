"""Syntax, default-deny and synthetic localhost checks; no remote opt in."""
import argparse
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'ansible' / 'tests'))
from ssh_guard_fixtures import generate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    env = dict(os.environ)
    env['ANSIBLE_CONFIG'] = str(ROOT / 'ansible' / 'ansible.cfg')
    engine = subprocess.run(['ansible-playbook', '--version'], env=env,
                            capture_output=True, text=True, check=True).stdout.splitlines()[0]
    for play in ('site.yml', 'precheck.yml', 'harden_svc_ansible_key.yml'):
        subprocess.run(['ansible-playbook', '-i', str(ROOT / 'ansible/inventory/example.yml'),
                        '--syntax-check', str(ROOT / 'ansible/playbooks' / play)],
                       cwd=ROOT / 'ansible', env=env, timeout=60, check=True)
        denied = subprocess.run(['ansible-playbook', '-i', str(ROOT / 'ansible/inventory/example.yml'),
                                 str(ROOT / 'ansible/playbooks' / play)],
                                cwd=ROOT / 'ansible', env=env, timeout=60,
                                capture_output=True, text=True)
        assert denied.returncode == 2, 'DEFAULT_DENY_NOT_CONFIRMED'
        assert 'Public example: remote execution is disabled by default.' in denied.stdout
        assert re.search(r'unreachable=0\s+failed=1', denied.stdout), 'REMOTE_ATTEMPT_OR_WRONG_FAILURE'
        skipped = subprocess.run(['ansible-playbook', '-i', str(ROOT / 'ansible/inventory/example.yml'),
                                  '--skip-tags', 'always', str(ROOT / 'ansible/playbooks' / play)],
                                 cwd=ROOT / 'ansible', env=env, timeout=60,
                                 capture_output=True, text=True)
        assert skipped.returncode == 0, 'CONDITIONAL_WORK_SKIP_FAILED'
        assert re.search(r'changed=0\s+unreachable=0\s+failed=0', skipped.stdout)
    for tag in ('common', 'k8s_prereq'):
        tagged = subprocess.run(['ansible-playbook', '-i', str(ROOT / 'ansible/inventory/example.yml'),
                                 '--tags', tag, str(ROOT / 'ansible/playbooks/site.yml')],
                                cwd=ROOT / 'ansible', env=env, timeout=60,
                                capture_output=True, text=True)
        assert tagged.returncode == 2
        assert 'Public example: remote execution is disabled by default.' in tagged.stdout
        assert re.search(r'unreachable=0\s+failed=1', tagged.stdout)
    resumed = subprocess.run(['ansible-playbook', '-i', str(ROOT / 'ansible/inventory/example.yml'),
                              '--start-at-task', 'Count managed SSH keys',
                              str(ROOT / 'ansible/playbooks/harden_svc_ansible_key.yml')],
                             cwd=ROOT / 'ansible', env=env, timeout=60,
                             capture_output=True, text=True)
    assert resumed.returncode == 0
    assert re.search(r'changed=0\s+unreachable=0\s+failed=0', resumed.stdout)
    with tempfile.TemporaryDirectory(prefix='toolkit-guards-') as temp:
        directory = Path(temp)
        cases = generate(ROOT / 'ansible/playbooks/harden_svc_ansible_key.yml', directory)
        subprocess.run(['ansible-playbook', '-i', 'localhost,', '-c', 'local',
                        str(directory / 'regression.yml')], cwd=directory, env=env,
                       timeout=300, check=True)
        results = []
        for case in cases:
            value = json.loads((directory / f"result-{case['case']}-{case['index']}.json").read_text())
            expected = case['expected_failure']
            assert type(value.get('failed_when_result')) is bool
            assert type(value.get('failed')) is bool
            assert value['failed_when_result'] == value['failed'] == expected
            assert type(value.get('rc')) is int and value['rc'] == case['expected_rc']
            assert value['stdout'].strip() == case['expected_count']
            results.append(dict(case=case['case'], guard=case['guard'],
                                expected_rejection=expected, contract_passed=True))
    report = {'engine': engine, 'syntax_playbooks': 3, 'default_deny_checks': 3,
              'skip_always_checks': 3, 'selected_tag_checks': 2, 'start_at_task_checks': 1, 'fixture_inputs': 7,
              'guard_results': len(results), 'scope': 'synthetic localhost only',
              'remote_execution': False, 'results': results}
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + '\n', encoding='utf-8')
    print(rendered)


if __name__ == '__main__':
    main()
