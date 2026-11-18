# Synthetic localhost fixtures. The key text is intentionally not a usable key.
"""Source extraction and synthetic fixtures; requires PyYAML, never Ansible."""
import copy
import json
from pathlib import Path

import yaml

NAMES = ['Count managed SSH keys', 'Verify restricted managed SSH key']
PLAIN = 'ssh-ed25519 AAAATESTFIXTURE managed-automation automation\n'
RESTRICTED = 'from="192.0.2.10",restrict ' + PLAIN
FIXTURES = {'empty': '', 'one_plain': PLAIN, 'one_restricted': RESTRICTED,
            'two_plain': PLAIN * 2, 'two_restricted': RESTRICTED * 2,
            'mixed': PLAIN + RESTRICTED, 'missing': None}
VALID = [{'one_plain', 'one_restricted'}, {'one_restricted', 'mixed'}]
COUNTS = {'empty': (0, 0), 'one_plain': (1, 0), 'one_restricted': (1, 1),
          'two_plain': (2, 0), 'two_restricted': (2, 2), 'mixed': (2, 1)}


def extract(source):
    play = yaml.safe_load(Path(source).read_text(encoding='utf-8'))[0]
    blocks = play['tasks']
    if (len(blocks) != 1 or set(blocks[0]) != {'name', 'when', 'block'}
            or blocks[0]['when'] != 'toolkit_allow_remote_execution | default(false) | bool'):
        raise ValueError('Expected explicit remote execution condition')
    source_tasks = blocks[0]['block']
    guards = []
    for name in NAMES:
        matches = [task for task in source_tasks if task.get('name') == name]
        if len(matches) != 1:
            raise ValueError(f'Expected exactly one source guard: {name}')
        task = copy.deepcopy(matches[0])
        allowed = {'name', 'ansible.builtin.command', 'register', 'changed_when',
                   'check_mode', 'failed_when'}
        if set(task) - allowed or task.get('changed_when') is not False:
            raise ValueError(f'Unexpected source guard shape: {name}')
        command = task['ansible.builtin.command']
        argv = command['argv']
        if set(command) != {'argv'} or len(argv) != 4 or argv[:2] != ['grep', '-cE']:
            raise ValueError(f'Expected read-only grep count: {name}')
        if not isinstance(task['register'], str) or 'failed_when' not in task:
            raise ValueError(f'Missing guard observation contract: {name}')
        guards.append(task)
    return guards, play['vars']


def cases():
    for case in FIXTURES:
        for index, name in enumerate(NAMES):
            count = '' if case == 'missing' else str(COUNTS[case][index])
            yield {'case': case, 'guard': name, 'index': index,
                   'expected_failure': case not in VALID[index],
                   'expected_rc': 2 if case == 'missing' else (1 if count == '0' else 0),
                   'expected_count': count}


def generate(source, destination):
    """Preserve the three exported filenames and six files + absent fixture."""
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    fixture_root = destination / 'fixtures'
    fixture_root.mkdir(exist_ok=True)
    if (fixture_root / 'missing').exists() or (fixture_root / 'missing').is_symlink():
        raise ValueError('Missing-file fixture already exists; use a new export directory')
    guards, variables = extract(source)
    for case, data in FIXTURES.items():
        if data is not None:
            path = fixture_root / case
            if path.is_symlink():
                raise ValueError('Fixture must not be a symlink')
            path.write_text(data, encoding='utf-8')
    tasks = []
    for case in cases():
        index = case['index']
        task = copy.deepcopy(guards[index])
        task['ansible.builtin.command']['argv'][-1] = str(fixture_root / case['case'])
        task['name'] = f"Execute source guard: {case['case']}: {case['guard']}"
        task['ignore_errors'] = True
        register = task['register']
        result_path = destination / f"result-{case['case']}-{index}.json"
        tasks.extend([
            task,
            {'name': 'Persist guard observation', 'ansible.builtin.copy': {
                'dest': str(result_path), 'mode': '0600',
                'content': '{{ ' + register + ' | to_json }}'}},
            {'name': f"Assert contract: {case['case']}: {index}",
             'ansible.builtin.assert': {'that': [
                 register + '.failed_when_result is boolean',
                 register + '.failed_when_result == ' + str(case['expected_failure']),
                 register + '.failed == ' + str(case['expected_failure']),
                 register + '.rc == ' + str(case['expected_rc']),
                 '(' + register + '.stdout | trim) == ' + repr(case['expected_count']),
             ]}, 'ignore_errors': True},
        ])
    assertions = []
    for index, task in enumerate(tasks):
        if 'ansible.builtin.assert' in task:
            name = f'contract_{index}'
            task['register'] = name
            assertions.append(name + ' is succeeded')
    tasks.append({'name': 'Require every fixture contract',
                  'ansible.builtin.assert': {'that': assertions}})
    play = [{'name': 'SSH guard localhost regression', 'hosts': 'localhost',
             'connection': 'local', 'gather_facts': False, 'become': False,
             'tasks': tasks}]
    for filename, data in [('ssh-guards.yml', guards), ('regression.yml', play)]:
        (destination / filename).write_text(yaml.safe_dump(data, sort_keys=False), encoding='utf-8')
    (destination / 'source-vars.json').write_text(json.dumps(variables, indent=2) + '\n', encoding='utf-8')
    return list(cases())
