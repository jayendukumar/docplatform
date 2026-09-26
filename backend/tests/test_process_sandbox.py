import os
import subprocess

from app.process_sandbox import isolated_process_options


def test_document_engine_processes_are_started_in_a_killable_group():
    options = isolated_process_options()
    if os.name == "posix":
        assert options == {"start_new_session": True}
    elif hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
        assert options == {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    else:
        assert options == {}
