import asyncio

async def run_command(cmd):
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
            raise ChildProcessError()
        return False, stdout.decode()

    return True, stdout.decode()

