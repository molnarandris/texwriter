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

