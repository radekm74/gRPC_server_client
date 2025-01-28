"""Simple gRPC client"""
import sys
import asyncio
from grpc import aio, StatusCode
import client_service_pb2
import client_service_pb2_grpc


async def run():
    """Main gRPC client routine"""
    async with aio.insecure_channel("localhost:50051") as channel:
        stub = client_service_pb2_grpc.ClientServiceStub(channel)

        while True:
            print("\nOptions:\n \t1. Send Message\n\t2. Get Client Status\n\t3. Exit")
            choice = input("Select an option: ")
            print()
            sys.stdout.flush()

            match choice:
                case "1":
                    client_id = input("Enter client ID: ")
                    message = input("Enter message (Hello/Goodbye): ")

                    try:
                        response = await stub.SendMessage(
                            client_service_pb2.MessageRequest(
                                client_id=client_id, message=message
                            )
                        )
                        print(f"Server Response: {response.info}")
                    except aio.AioRpcError as e:
                        if e.code() == StatusCode.INVALID_ARGUMENT:
                            print("Invalid argument error:", e.details())
                        elif e.code() == StatusCode.NOT_FOUND:
                            print("Not found error:", e.details())
                        else:
                            print(f"Unexpected gRPC error: {e.code()}, details: {e.details()}")

                case "2":
                    client_id = input("Enter client ID (leave empty for all clients): ")
                    try:
                        response = await stub.GetClientStatus(
                            client_service_pb2.ClientStatusRequest(client_id=client_id)
                        )
                        for cid, status in response.statuses.items():
                            print(f"Client ID: {cid}, Status: {status}")
                    except aio.AioRpcError as e:
                        if e.code() == StatusCode.NOT_FOUND:
                            print("Client not found:", e.details())
                        else:
                            print(f"Unexpected gRPC error: {e.code()}, details: {e.details()}")

                case "3":
                    print("Exiting client.")
                    break

                case _:
                    print("Invalid choice. Please try again.")


if __name__ == "__main__":
    asyncio.run(run())
