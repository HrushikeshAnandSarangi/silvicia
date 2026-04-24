import asyncio
import time
from django.core.management.base import BaseCommand
from core.models import Task
from asgiref.sync import async_to_sync, sync_to_async
from channels.layers import get_channel_layer

class Command(BaseCommand):
    help = 'Starts the simulated worker fleet to process tasks'

    def handle(self, *args, **options):
        self.stdout.write("Starting 3 virtual workers...")
        asyncio.run(self.run_workers())

    async def run_workers(self):
        worker_ids = [1, 2, 3]
        tasks = [self.worker_loop(w_id) for w_id in worker_ids]
        await asyncio.gather(*tasks)

    async def worker_loop(self, worker_id):
        channel_layer = get_channel_layer()

        while True:
            # Atomic fetch-and-update to avoid race conditions between workers
            task = await self.grab_pending_task(worker_id)
            if task:
                self.stdout.write(f"Worker {worker_id} acquired Task {task.id}")
                
                # Notify UI of PROCESSING
                await channel_layer.group_send("dashboard", {
                    "type": "send_update", 
                    "message": f"Worker {worker_id} processing task."
                })
                
                # Simulate 2 seconds processing
                await asyncio.sleep(2)
                
                # Complete the task
                await self.complete_task(task.id)
                self.stdout.write(f"Worker {worker_id} completed Task {task.id}")
                
                # Notify UI of COMPLETED
                await channel_layer.group_send("dashboard", {
                    "type": "send_update", 
                    "message": f"Worker {worker_id} completed task."
                })
            else:
                # No tasks available, wait a bit before checking again
                await asyncio.sleep(1)

    @sync_to_async
    def grab_pending_task(self, worker_id):
        # We find one PENDING task
        task = Task.objects.filter(status='PENDING').first()
        if task:
            task.status = 'PROCESSING'
            task.worker_id = worker_id
            task.save()
            return task
        return None

    @sync_to_async
    def complete_task(self, task_id):
        task = Task.objects.get(id=task_id)
        task.status = 'COMPLETED'
        task.save()
