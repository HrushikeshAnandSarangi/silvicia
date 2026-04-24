import json
from channels.generic.websocket import AsyncWebsocketConsumer

class DashboardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("dashboard", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("dashboard", self.channel_name)

    async def receive(self, text_data):
        # We don't really receive anything complex from UI yet
        pass

    async def send_update(self, event):
        message = event['message']
        await self.send(text_data=json.dumps({
            'message': message
        }))
