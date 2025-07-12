from channels.generic.websocket import AsyncWebsocketConsumer
import json

class ContributeConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer broadcasting contribute page updates."""

    async def connect(self):
        # Join the shared group so all clients receive updates.
        await self.channel_layer.group_add("contribute", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        # Leave the group when the socket closes.
        await self.channel_layer.group_discard("contribute", self.channel_name)

    async def contribute_update(self, event):
        # Send a JSON payload to the browser with update info.
        await self.send(text_data=json.dumps(event.get("data", {})))
