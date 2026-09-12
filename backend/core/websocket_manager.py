from fastapi import WebSocket


class ConnectionManager:

    def __init__(self):

        self.connections = []


    async def connect(
        self,
        websocket
    ):

        await websocket.accept()

        self.connections.append(
            websocket
        )


    def disconnect(
        self,
        websocket
    ):

        self.connections.remove(
            websocket
        )


    async def broadcast(
        self,
        message
    ):

        for connection in self.connections:

            await connection.send_json(
                message
            )


manager = ConnectionManager()
