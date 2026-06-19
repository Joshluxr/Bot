import os
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path

from .database import (
    append_job_log,
    create_job_record,
    get_all_settings_dict,
    log_audit,
    update_job,
)

PANEL_ROOT = Path(__file__).resolve().parent.parent

TOOLS = {
    'waf_bypass_probe': {
        'name': 'WAF Bypass Probe',
        'description': 'Read-only AUTHZ-VULN-01 CloudFront WAF bypass probe on wp-login.php',
        'script': 'waf_bypass_probe.py',
        'needs_target': True,
    },
    'engagement_recon': {
        'name': 'Engagement Recon',
        'description': 'Passive reconnaissance and fingerprinting',
        'script': 'engagement_recon.py',
        'needs_target': False,
    },
    'offensive_assessment': {
        'name': 'Offensive Assessment (Phase 1)',
        'description': 'Aggressive WordPress assessment — phase 1',
        'script': 'offensive_assessment.py',
        'needs_target': True,
    },
    'phase2_offensive': {
        'name': 'Phase 2 Offensive',
        'description': 'Expanded brute force and Elementor/CVE checks',
        'script': 'phase2_offensive.py',
        'needs_target': True,
    },
    'phase3_aggressive': {
        'name': 'Phase 3 Aggressive',
        'description': 'Parallel brute force with rockyou wordlist',
        'script': 'phase3_aggressive.py',
        'needs_target': True,
    },
    'decepticon_runner': {
        'name': 'Decepticon Attack Runner',
        'description': 'Nuclei, httpx, ffuf skill playbooks',
        'script': 'decepticon_attack_runner.py',
        'needs_target': True,
    },
    'bruter': {
        'name': 'WordPress Bruter',
        'description': 'Multi-site WordPress credential checker',
        'script': 'BRUTER.py',
        'needs_target': False,
    },
}

_running: dict[int, subprocess.Popen] = {}
_lock = threading.Lock()
_running_count = 0


def _tool_dir() -> Path:
    settings = get_all_settings_dict()
    rel = settings.get('wordpress_tool_dir', '../wordpress-tool')
    return (PANEL_ROOT / rel).resolve()


def _build_cmd(tool: str, target: str, params: dict) -> list[str]:
    meta = TOOLS[tool]
    path = _tool_dir() / meta['script']
    if not path.exists():
        raise FileNotFoundError(f'Script not found: {path}')
    cmd = ['python3', str(path)]
    if tool == 'bruter':
        site_file = params.get('site_file') or str(_tool_dir() / 'sites' / 'engagement.txt')
        cmd.append(site_file)
    elif meta['needs_target']:
        cmd.append(target or params.get('target', ''))
    return cmd


def _env() -> dict[str, str]:
    settings = get_all_settings_dict()
    env = os.environ.copy()
    tools_bin = (PANEL_ROOT / settings.get('tools_bin', '../decepticon-tools/bin')).resolve()
    env['PATH'] = f'{tools_bin}:{env.get("PATH", "")}'
    if settings.get('ato_spray_enabled') == 'true':
        env['ATO_SPRAY'] = '1'
    if settings.get('custom_openai_api_base'):
        env['CUSTOM_OPENAI_API_BASE'] = settings['custom_openai_api_base']
    if settings.get('custom_openai_api_key'):
        env['CUSTOM_OPENAI_API_KEY'] = settings['custom_openai_api_key']
    if settings.get('custom_openai_model'):
        env['CUSTOM_OPENAI_MODEL'] = settings['custom_openai_model']
    return env


def _can_start() -> bool:
    settings = get_all_settings_dict()
    max_jobs = int(settings.get('max_parallel_jobs', '2'))
    with _lock:
        return _running_count < max_jobs


def start_job(tool: str, target: str, params: dict, user_id: int) -> int:
    global _running_count
    name = params.get('name') or f'{TOOLS[tool]["name"]} — {target or "default"}'
    job_id = create_job_record(name, tool, target, user_id)
    log_audit(user_id, 'job_create', 'job', f'{tool}:{target}')

    if not _can_start():
        update_job(job_id, status='failed', exit_code=-1, finished_at=datetime.now(timezone.utc).isoformat())
        append_job_log(job_id, 'Max parallel jobs reached. Increase max_parallel_jobs or wait.\n')
        return job_id

    def run() -> None:
        global _running_count
        log_path = PANEL_ROOT / 'data' / 'logs' / f'job_{job_id}.log'
        log_path.parent.mkdir(parents=True, exist_ok=True)
        proc: subprocess.Popen | None = None
        try:
            cmd = _build_cmd(tool, target, params)
            update_job(
                job_id,
                status='running',
                started_at=datetime.now(timezone.utc).isoformat(),
            )
            with open(log_path, 'w', encoding='utf-8') as logf:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=str(_tool_dir()),
                    env=_env(),
                )
                with _lock:
                    _running[job_id] = proc
                update_job(job_id, pid=proc.pid, output_path=str(log_path))
                for line in proc.stdout or []:
                    logf.write(line)
                    logf.flush()
                    append_job_log(job_id, line)
                proc.wait()
                status = 'completed' if proc.returncode == 0 else 'failed'
                update_job(
                    job_id,
                    status=status,
                    exit_code=proc.returncode,
                    finished_at=datetime.now(timezone.utc).isoformat(),
                )
        except Exception as exc:
            append_job_log(job_id, f'\n[ERROR] {exc}\n')
            update_job(
                job_id,
                status='failed',
                exit_code=-1,
                finished_at=datetime.now(timezone.utc).isoformat(),
            )
        finally:
            with _lock:
                _running.pop(job_id, None)
                _running_count -= 1
            if proc and proc.poll() is None:
                proc.kill()

    with _lock:
        _running_count += 1
    threading.Thread(target=run, daemon=True).start()
    return job_id


def stop_job(job_id: int, user_id: int) -> bool:
    with _lock:
        proc = _running.get(job_id)
    if not proc or proc.poll() is not None:
        return False
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    update_job(job_id, status='stopped', finished_at=datetime.now(timezone.utc).isoformat(), exit_code=-9)
    log_audit(user_id, 'job_stop', 'job', str(job_id))
    append_job_log(job_id, '\n[JOB STOPPED BY ADMIN]\n')
    return True
