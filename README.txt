Simple User Connection Management System

Date: 2025.01.26
Version: 1.0
Author: Radoslaw Mielczarek

Requirements
    Python Version: 3.13 or above

Required Libraries:
    pytest
    grpcio
    grpcio-tools
    protobuf
    pytest-asyncio
    allure-pytest (for Allure test generation)

Description
This system simulates a user connection management system. It consists of two components:
    1) gRPC server
    2) gRPC client
    3) tests
Both components are implemented in Python.

Usage
    Running the Server
        1) Open a terminal (Command Prompt on Windows).
        2) Execute the following command:
            python server.py
    Running the Client
        1) Open a second terminal.
        2) Execute the following command:
            python client.py

    Interacting with the Client
        Upon running the client application, you will see the following menu:
            1. Send Message
            2. Get Client Status
            3. Exit

        Option 1: Send Message
            a) Select option 1 and press Enter.
            b) Enter a client ID (any combination of letters and numbers) and press Enter.
            c) Enter a message:
                Type Hello to mark the user as connected.
                Type Goodbye to mark the user as disconnected.
            d) The server will respond with a message like:
                Server Response: Client <client_name> marked as connected.

            You can repeat this process to create or update the status of another user.

        Option 2: Get Client Status
            a) Select option 2 and press Enter.
            b) Enter the name of a specific user to check their status,
                or press Enter without input to retrieve the status of all registered users.
            c) The server will display the requested status information.

        Option 3: Exit
            a) To close the client application, select option 3 and press Enter.

    Multi-Client Usage
        You can run the client application in multiple terminals simultaneously.
        Each instance of the client will connect to the same server,
        allowing you to manage and query user statuses from different sessions.

    Example Workflow
        1) Start the server in one terminal.
        2) Start the client in another terminal.
        3) Use the client to:
            a) Register or update users with Hello or Goodbye messages.
            b) Retrieve the statuses of registered users.
        4) Open additional terminals and start more client instances, interacting with the same server.

    There are test provided with the system. To run test execute:
        pytest test_grpc_system.py


Additional info Allure Report:
Windows installing:
    Execute in PowerShell:
        Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
        Invoke-RestMethod -Uri https://get.scoop.sh | Invoke-Expression
        scoop install allure

    Install java RTE (for example from Oracle)

To create test with Allure report execute:
    pytest test_grpc_system.py --alluredir=allure-results

To generata and view reports:
     allure serve allure-results
