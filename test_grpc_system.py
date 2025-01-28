"""Tests for gRPC Client-Server"""

import time
import logging as logger
import asyncio
import subprocess
from threading import Thread
import pytest_asyncio
import pytest
from grpc import aio
import client_service_pb2
import client_service_pb2_grpc
from server import ClientService


TEST_USERS = ["1", "user_1", "User_001"]
SERVER_ADDRESS = "localhost:50051"
OUT_CLIENT = ""
OUT_SERVER = ""


def read_output_c(process):
    global OUT_CLIENT
    while True:
        output = process.stdout.readline()
        if output == b"" and process.poll() is not None:
            break
        if output.strip():
            logger.info(f"Client output: {output.strip()}")
            OUT_CLIENT += output.strip()


def read_output_s(process):
    global OUT_SERVER
    while True:
        output = process.stdout.readline()
        if output == b"" and process.poll() is not None:
            break
        if output.strip():
            logger.info(f"Server output: {output.strip()}")
            OUT_SERVER += output.strip()


@pytest.fixture()
def client():
    process = subprocess.Popen(
        "python client.py",
        shell=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(1)
    yield process
    process.terminate()
    process.wait()


@pytest_asyncio.fixture()
async def grpc_server():
    """Start gRPC server."""
    server = aio.server()
    client_service_pb2_grpc.add_ClientServiceServicer_to_server(ClientService(), server)
    port = server.add_insecure_port("[::]:50051")
    logger.info("Server is starting on port 50051.")
    await server.start()
    yield f"localhost:{port}"
    await server.stop(1)
    logger.info("Server down.")


async def simulate_client(client_id, messages):
    """Simulate client, open channel and sends a message or a list of messages"""
    if not isinstance(messages, list):
        messages = [
            messages,
        ]
    async with aio.insecure_channel(SERVER_ADDRESS) as channel:
        grpc_client = client_service_pb2_grpc.ClientServiceStub(channel)
        responses = []
        for message in messages:
            response = await grpc_client.SendMessage(
                client_service_pb2.MessageRequest(client_id=client_id, message=message)
            )
            responses.append(response)
            logger.info(f"Client {client_id} received: {response.info}")
        return responses


@pytest.mark.asyncio(loop_scope="function")
@pytest.mark.parametrize("user", TEST_USERS)
async def test_send_message_hello(grpc_server, user):
    """Send 'Hello' message and check response."""
    logger.info(f"Test if user is connected when Hello message is sent for user: {user}")
    task = simulate_client(user, "Hello")
    responses = await asyncio.gather(task)
    response = responses[0][0]
    assert response.success is True, f"Incorrect response: {response.success}"
    assert "marked as connected" in response.info, f"Incorrect response info: {response.info}"


@pytest.mark.asyncio(loop_scope="function")
@pytest.mark.parametrize("user", TEST_USERS)
async def test_send_message_goodbye(grpc_server, user):
    """Send 'Goodbye' message and check response."""
    logger.info(f"Test if user is disconnected when Goodbye message is sent for user: {user}")
    task = simulate_client(user, "Goodbye")
    responses = await asyncio.gather(task)
    response = responses[0][0]
    assert response.success is True, f"Incorrect response: {response.success}"
    assert (
        "marked as disconnected" in response.info
    ), f"Incorrect response info: {response.info}"


@pytest.mark.asyncio(loop_scope="function")
async def test_send_message_invalid(grpc_server):
    """Send  invalid message and check response."""
    async with aio.insecure_channel(SERVER_ADDRESS) as channel:
        grpc_client = client_service_pb2_grpc.ClientServiceStub(channel)
        with pytest.raises(Exception) as excinfo:
            await grpc_client.SendMessage(
                client_service_pb2.MessageRequest(
                    client_id="test_user", message="InvalidMessage"
                )
            )
        assert "StatusCode.INVALID_ARGUMENT" in str(excinfo.value)
        assert "Invalid message type" in str(excinfo.value)


@pytest.mark.asyncio(loop_scope="function")
async def test_check_status_connected(grpc_server):
    """Send 'Hello' message and check response."""
    async with aio.insecure_channel(SERVER_ADDRESS) as channel:
        grpc_client = client_service_pb2_grpc.ClientServiceStub(channel)
        response = await grpc_client.SendMessage(
            client_service_pb2.MessageRequest(client_id="test_user", message="Hello")
        )
        assert response.success is True
        assert "marked as connected" in response.info
        response = await grpc_client.GetClientStatus(
            client_service_pb2.ClientStatusRequest(client_id="test_user")
        )
        for cid, status in response.statuses.items():
            logger.info(f"Client ID: {cid}, Status: {status}")
            assert cid == "test_user"
            assert status == "connected"


@pytest.mark.asyncio(loop_scope="function")
async def test_check_status_disconnected(grpc_server):
    """Send 'Hello' followed by 'Goodbye' message and check user status."""
    async with aio.insecure_channel(SERVER_ADDRESS) as channel:
        grpc_client = client_service_pb2_grpc.ClientServiceStub(channel)
        await grpc_client.SendMessage(
            client_service_pb2.MessageRequest(client_id="test_user", message="Hello")
        )

        grpc_client = client_service_pb2_grpc.ClientServiceStub(channel)
        await grpc_client.SendMessage(
            client_service_pb2.MessageRequest(client_id="test_user", message="Goodbye")
        )

        response = await grpc_client.GetClientStatus(
            client_service_pb2.ClientStatusRequest(client_id="test_user")
        )
        for cid, status in response.statuses.items():
            logger.info(f"Client ID: {cid}, Status: {status}")
            assert cid == "test_user"
            assert status == "disconnected"


@pytest.mark.asyncio(loop_scope="function")
async def test_check_status_specific(grpc_server):
    """Check statuses for multiple users."""
    async with aio.insecure_channel(SERVER_ADDRESS) as channel:
        grpc_client = client_service_pb2_grpc.ClientServiceStub(channel)
        for user, message in [
            ("test_user_1", "Hello"),
            ("test_user_2", "Goodbye"),
            ("test_user_3", "Hello"),
        ]:
            await grpc_client.SendMessage(
                client_service_pb2.MessageRequest(client_id=user, message=message)
            )

        for user, message in [
            ("test_user_1", "connected"),
            ("test_user_2", "disconnected"),
            ("test_user_3", "connected"),
        ]:
            response = await grpc_client.GetClientStatus(
                client_service_pb2.ClientStatusRequest(client_id=user)
            )
            for cid, status in response.statuses.items():
                logger.info(f"Client ID: {cid}, Status: {status}")
                assert cid == user
                assert status == message


@pytest.mark.asyncio(loop_scope="function")
async def test_get_client_status_all(grpc_server):
    """Test retrieving status of all users."""

    async with aio.insecure_channel(SERVER_ADDRESS) as channel:
        grpc_client = client_service_pb2_grpc.ClientServiceStub(channel)
        response = await grpc_client.SendMessage(
            client_service_pb2.MessageRequest(client_id="user1", message="Hello")
        )
        assert response.success is True
        assert "marked as connected" in response.info

        response = await grpc_client.SendMessage(
            client_service_pb2.MessageRequest(client_id="user2", message="Goodbye")
        )
        assert response.success is True
        assert "marked as disconnected" in response.info

        response = await grpc_client.GetClientStatus(
            client_service_pb2.ClientStatusRequest(client_id="")
        )
        assert response.statuses["user1"] == "connected"
        assert response.statuses["user2"] == "disconnected"


@pytest.mark.asyncio(loop_scope="function")
async def test_simulate_multiple_clients(grpc_server):
    """Test simulating multiple clients."""
    clients = [
        {
            "user_id": "user_1",
            "messages": [
                "Hello",
            ],
            "status": "connected",
        },
        {"user_id": "user_2", "messages": ["Hello", "Goodbye"], "status": "disconnected"},
        {
            "user_id": "user_3",
            "messages": [
                "Goodbye",
            ],
            "status": "disconnected",
        },
        {"user_id": "user_4", "messages": ["Hello"], "status": "connected"},
        {"user_id": "user_5", "messages": ["Goodbye", "Hello"], "status": "connected"},
        {
            "user_id": "user_6",
            "messages": ["Goodbye", "Hello", "Goodbye"],
            "status": "disconnected",
        },
    ]

    tasks = [simulate_client(client["user_id"], client["messages"]) for client in clients]
    await asyncio.gather(*tasks)

    # Check if all users have correct status
    async with aio.insecure_channel(SERVER_ADDRESS) as channel:
        grpc_client = client_service_pb2_grpc.ClientServiceStub(channel)
        response = await grpc_client.GetClientStatus(
            client_service_pb2.ClientStatusRequest(client_id="")
        )
    # Check end status of all users:
    for client in clients:
        assert response.statuses[client["user_id"]] == client["status"]


def test_end_to_end_test_valid():
    """Test end-to-end."""
    global OUT_CLIENT
    OUT_CLIENT = ""
    server_process = subprocess.Popen(
        ["python", "server.py"],
        shell=False,
        text=True,
        bufsize=1,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    client_process = subprocess.Popen(
        ["python", "client.py"],
        shell=False,
        text=True,
        bufsize=1,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(1)
    try:
        thread = Thread(target=read_output_c, args=(client_process,))
        thread.daemon = True
        thread.start()

        commands = [
            "1",
            "user1",
            "Hello",
            "2",
            "",
        ]

        for cmd in commands:
            logger.info(f"Sending command: {cmd}")
            client_process.stdin.write(cmd + "\n")
            client_process.stdin.flush()
            time.sleep(0.5)

        assert "Client user1 marked as connected" in OUT_CLIENT
        assert "Client ID: user1, Status: connected" in OUT_CLIENT

    except Exception as e:
        print(e)

    finally:
        client_process.terminate()
        client_process.wait()
        server_process.terminate()
        server_process.wait()


def test_end_to_end_test_invalid():
    """Test end-to-end."""
    global OUT_CLIENT
    global OUT_SERVER
    server_process = subprocess.Popen(
        ["python", "server.py"],
        shell=False,
        text=True,
        bufsize=1,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    client_process = subprocess.Popen(
        ["python", "client.py"],
        shell=False,
        text=True,
        bufsize=1,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(1)
    try:
        thread_client = Thread(target=read_output_c, args=(client_process,))
        thread_client.daemon = True
        thread_client.start()

        thread_server = Thread(target=read_output_s, args=(server_process,))
        thread_server.daemon = True
        thread_server.start()

        commands = [
            "1",
            "user1",
            "Hello",
            "1",
            "user1",
            "Hurrah",
            "1",
            "user1",
            "Goodbye",
        ]

        for cmd in commands:
            logger.info(f"Sending command: {cmd}")
            client_process.stdin.write(cmd + "\n")
            client_process.stdin.flush()
            time.sleep(0.5)
            if cmd == "Hello":
                logger.info("Checking if user1 is marked as connected.")
                assert "Client user1 marked as connected." in OUT_CLIENT
                OUT_CLIENT = ""
            elif cmd == "Hurrah":
                logger.info("Checking invalid command.")
                assert "Invalid argument error: Invalid message type: Hurrah" in OUT_CLIENT
                assert "Warning: Invalid message type: Hurrah" in OUT_SERVER
                OUT_CLIENT = ""
                OUT_SERVER = ""
            elif cmd == "Goodbye":
                logger.info("Checking if user1 is marked as disconnected.")
                assert "Client user1 marked as disconnected." in OUT_CLIENT
                OUT_CLIENT = ""

    except Exception as e:
        print(e)

    finally:
        client_process.terminate()
        client_process.wait()
        server_process.terminate()
        server_process.wait()
