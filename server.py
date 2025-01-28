"""Simple gRPC server"""

import sys
import asyncio
from grpc import aio, StatusCode
import client_service_pb2
import client_service_pb2_grpc


class ClientService(client_service_pb2_grpc.ClientServiceServicer):
    """A class for handling messages from customers"""

    messages = {"connect": "hello", "disconnect": "goodbye"}

    def __init__(self):
        self.client_statuses = {}

    async def SendMessage(self, request, context):
        client_id = request.client_id
        message = request.message.lower()

        # Message processing
        if message == self.messages["connect"]:
            self.client_statuses[client_id] = "connected"
            info = f"Client {client_id} marked as connected."
        elif message == self.messages["disconnect"]:
            self.client_statuses[client_id] = "disconnected"
            info = f"Client {client_id} marked as disconnected."
        else:
            info = f"Invalid message type: {request.message}"
            print(f"Warning: {info}")
            sys.stdout.flush()
            await context.abort(StatusCode.INVALID_ARGUMENT, info)

        return client_service_pb2.MessageResponse(success=True, info=info)

    async def GetClientStatus(self, request, context):
        if request.client_id:
            if request.client_id in self.client_statuses:
                return client_service_pb2.ClientStatusResponse(
                    statuses={request.client_id: self.client_statuses[request.client_id]}
                )
            else:
                info = f"Client {request.client_id} not found"
                print(f"Warning: {info}")
                sys.stdout.flush()
                await context.abort(StatusCode.NOT_FOUND, info)
        else:
            return client_service_pb2.ClientStatusResponse(statuses=self.client_statuses)


async def serve():
    server = aio.server()
    client_service_pb2_grpc.add_ClientServiceServicer_to_server(ClientService(), server)
    server.add_insecure_port("[::]:50051")

    # Start server
    print("Server is starting on port 50051.")
    sys.stdout.flush()
    await server.start()

    # Graceful shutdown handler
    stop_event = asyncio.Event()

    async def check_for_shutdown():
        while not stop_event.is_set():
            await asyncio.sleep(1)

    async def shutdown():
        print("\nShutting down gracefully...")
        await server.stop(5)  # Allow 5 seconds for ongoing requests to complete
        await server.wait_for_termination()
        print("Server stopped.")
        sys.stdout.flush()

    # Run shutdown handler in background
    asyncio.create_task(check_for_shutdown())
    try:
        await stop_event.wait()
    finally:
        await shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        print("Server interrupted and stopped.")
