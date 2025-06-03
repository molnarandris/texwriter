import asyncio
import traceback

_background_tasks = set()

def task_done(task):
	_background_tasks.remove(task)
	exc = task.exception() # Also marks that the exception has been handled
	if exc:
	    traceback.print_exception(exc)

def create_task(awaitable):
	"""Spawn an awaitable as a stand-alone task"""
	task = asyncio.create_task(awaitable)
	_background_tasks.add(task)
	task.add_done_callback(task_done)
	return task

async def run_command_on_host(cmd):
    cmd = ["flatpak-spawn", "--host"] + cmd
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    try:
        stdout, stderr = await process.communicate()
    except asyncio.CancelledError:
        process.terminate()
        raise

    if process.returncode!=0:
        if stderr.decode().startswith("Portal call failed:"):
            raise ChildProcessError("Flatpak portal call failed")
        return False, stdout.decode()

    return True, stdout.decode()

