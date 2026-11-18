# PMO Delivery Toolkit

일정과 요구사항 변경을 관리할 때는 작업 진행 상황뿐 아니라, 다음 단계로 넘어갈 조건과 확인할 근거도 필요합니다. 이 저장소는 FDS(이상금융거래탐지시스템) 교육 프로젝트에서 제가 맡았던 Python과 Ansible 구현물 중 그 기준을 코드로 확인할 수 있는 부분을 모았습니다.

제 경력의 중심은 IT PMO와 소프트웨어 품질관리입니다. 이 프로젝트에서는 하이브리드 환경의 아키텍처와 배포 경로를 설계하고, 서버 설정과 사전 점검을 자동화했습니다. Python으로 배포 상태를 관리하는 프로그램과 구성 파일을 수집해 해시를 대조하는 도구를 구현했습니다. 팀원이 수행한 AWS 자원 구성과 클라우드 통합 시험은 설계 조건 및 실행 기록과 대조해 검토했습니다.

**이 저장소의 Python 시험은 모의 환경과 합성 Git 자료를 사용합니다. 개인 배포 프로그램으로 실제 클라우드 자동 배포를 완료했다는 의미가 아닙니다.**

- [경력과 프로젝트 설명 — Notion](https://forested-walk-e30.notion.site/IT-PMO-3f970bc8a619817c852fdb9e5fef8d47)
- [321Team 공개 아키텍처](https://321team.github.io/fds-project-architecture/)
- [구현 설명과 실행 조건](docs/implementation.md)
- [역할과 검증 범위](docs/scope.md)
- [출처 및 공개용 변경 내역](docs/provenance.md)
- [재검증 결과](docs/verification.md)

## 무엇을 확인할 수 있나요?

| 구현물 | 관리하려는 문제 | 코드에서 확인할 내용 |
|---|---|---|
| Python 배포 코어 | 승인받은 대상이나 입력이 바뀐 채 작업이 진행되는 문제 | 대상, 이미지, 입력 해시와 승인 유효시간을 검사하고, 응답 유실이나 상태 불일치가 생기면 후속 변경을 중단합니다. |
| Python 구성 파일 수집 | 검토한 소스와 전달한 파일이 같은지 불분명한 문제 | 지정한 Git 커밋에서 허용된 파일만 읽고, Git 객체 식별자와 SHA-256으로 바이트를 대조합니다. |
| Ansible 서버 설정 | 서버마다 공통 설정이 달라지는 문제 | 시간 동기화, 호스트 정보와 Kubernetes 사전 조건을 코드로 관리합니다. |
| Ansible 사전 점검 | 설정 작업과 현재 상태 확인을 혼동하는 문제 | 설정을 바꾸는 작업과 읽기 전용 점검을 분리합니다. SSH 키 개수 검사도 합성 자료로 재현합니다. |

## 저장소 구성

```text
python/                 배포 코어, 구성 파일 수집 도구, 모의시험
ansible/playbooks/      서버 설정, 사전 점검, SSH 키 조건 검사
ansible/roles/          공통 설정과 Kubernetes 사전 조건
ansible/inventory/      실제 접속 대상이 없는 예시
ansible/tests/          합성 SSH 키 검사 자료
scripts/                공개 자료 점검과 로컬 검증
docs/                   역할, 출처, 실행 조건과 검증 결과
```

## 로컬 검증

Python 3.12 이상, Git의 `--no-lazy-fetch` 지원, PyYAML 6.0.3이 필요합니다. Python 시험은 임시 Git 저장소를 만들며 실제 클라우드나 서버에는 접속하지 않습니다.

```bash
python -m pip install -r requirements-test.txt
python -m unittest discover -s python -v
python scripts/check_public_tree.py
```

Ansible 검증은 Linux에서 ansible-core 2.20.11로 실행합니다. `scripts/verify_ansible.py`는 문법 검사, 기본 실행 차단 확인과 임시 폴더의 합성 자료 검사를 수행합니다.

```bash
python -m pip install -r requirements-ansible.txt
python scripts/verify_ansible.py
```

실제 서버용 플레이북은 기본 상태에서 원격 실행을 차단합니다. 예시 주소는 접속 정보가 아니며, 실제 환경에 적용하려면 대상과 권한, 복구 방법을 별도로 검토해야 합니다. 이 저장소에는 운영용 인증정보, 네트워크 전송 구현, 승인 서비스와 실행 잠금 서비스가 포함되어 있지 않습니다.

## 공개 범위

프로젝트는 2026년 8월부터 10월까지 진행한 교육 연계 팀 프로젝트입니다. 원본 공동 저장소의 선정된 파일을 공개용으로 정리했으며, 팀 전체의 구현을 개인 단독 성과로 표시하지 않습니다. 개인정보, 원본 인벤토리, 내부 주소, 인증정보와 실제 실행 로그는 포함하지 않았습니다. 예시 및 시험 데이터는 합성 자료입니다.

원본의 이용허락을 임의로 확대하지 않기 위해 별도의 오픈소스 라이선스는 부여하지 않았습니다. 출처와 변경 범위는 [provenance.md](docs/provenance.md)에 정리했습니다.
