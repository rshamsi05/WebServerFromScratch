## System Architecture Overview:
┌─────────────┐         ┌─────────────────────────────┐         ┌─────────────┐
│   Client    │◄───────►│      Server Process         │◄───────►│   Client    │
│  (Alice)    │  Socket │                             │  Socket │   (Bob)     │
└─────────────┘         │  ┌───────────────────────┐  │         └─────────────┘
                        │  │   Main Thread         │  │
                        │  │   (Accept Loop)       │  │
                        │  └──────────┬────────────┘  │
                        │             │               │
                        │      ┌──────▼──────┐        │
                        │      │ Shared State│        │         ┌─────────────┐
                        │      │  - clients  │        │◄───────►│   Client    │
                        │      │  - lock     │        │  Socket │  (Charlie)  │
                        │      └──────┬──────┘        │         └─────────────┘
                        │             │               │
                        │    ┌────────┴────────┐      │
                        │    │                 │      │
                        │ ┌──▼───┐  ┌────┐  ┌──▼───┐ │
                        │ │Thread│  │... │  │Thread│ │
                        │ │ for  │  │    │  │ for  │ │
                        │ │Alice │  │    │  │ Bob  │ │
                        │ └──────┘  └────┘  └──────┘ │
                        └─────────────────────────────┘


## Component Breakdown
1) Main Server Process(e.g Server.py)
- Purpose: Manages listening socket and creates client listeners
- Responsibilities
    - Create and bind listening socket to localhost:8888
    - Maintain shared state(list of connected clients)
    - Accept incoming requests in an infinite loop
    - Create new thread for each client connection
    - Handle graceful shutdown
    - Key Data Structure:
- Key Data Structure
    - ```clients = []  # List of connected client info: 
              # [{
              #    'socket': socket_obj,
              #    'username': 'Alice',
              #    'address': ('127.0.0.1', 54321),
              #    'connected_at': datetime
              # }, ...]

        clients_lock = threading.Lock()  # Prevents race conditions```
    - 
2) Client Handler Thread
- Purpose: Manages the threads lifecycle responsible for a specific client
- Responsibilites
    - Username Setup:
        - Prompt Client for Username
        - Validate username(non-empty, unique characters)
        - Register Client in shared clients list
        - Broadcast user has joined the chat
    - Message Loop
        - Continuously read messages from client socket
        - Validate message (non-empty, max X amount chars)
        - Add timestamp
        - Broadcast to all other clients
    - Cleanup on disconnect:
        - Detect when clients close connections
        - Remove client from shared clients list
        - Broadcast “User has left the chat” to remaining clients
        - Close socket and exit thread
    - Communication
        - IN: Messages from its assigned client socket
        - OUT:
            - Writes to shared clients list (with lock)
            - Calls broadcast() function to send to all clients
3) Broadcast Function
- Purpose:  Send message to all connected clients except sender
- Responsibilities:
    - Acquire lock on clients list
    - Iterate through all client sockets
    - Send message to each socket(skip sender)
    - Handle send failures(client disconnected mid-send)
- Signature:
    ```Python
    def broadcast(message, sender_socket=None):
        """
        Args:
            message: String to send to all clients
            sender_socket: Socket to exclude (don't echo back to sender)
        """
    ```

    **Error Handling:**
    - If send fails (broken socket), mark client for removal
    - Continue sending to other clients (don't let one failure stop others)

    ---

    ### 2. **Client Components**

    #### **Client Script (`client.py`)**

    **Purpose:** Simple terminal interface for users to connect and chat

    **Responsibilities:**
    1. **Connect to server:**
    - Create socket
    - Connect to `localhost:8888`

    2. **Two parallel tasks** (needs threading):
    - **Receive Thread:** Continuously listen for messages from server, print to terminal
    - **Send Thread (Main):** Read user input from terminal, send to server

    3. **Handle disconnection:**
    - Detect server shutdown
    - Clean exit on Ctrl+C

    **User Flow:**
    ```
    $ python client.py
    Connecting to chat server...
    Connected! Enter your username: Alice
    [14:32] Welcome to the chat, Alice!
    [14:32] Alice joined the chat
    [14:33] Bob: Hey Alice!
    > Hi Bob!                          # User types this
    [14:34] Alice: Hi Bob!             # Server echoes back
    > 
    ```

    **Communication:**
    - **OUT:** Sends username and messages to server socket
    - **IN:** Receives broadcasted messages from server socket

    ---

    ## Communication Flow Examples

    ### **Scenario 1: User Joins**
    ```
    1. Alice runs: python client.py
    
    2. Client connects to server socket
    
    3. Server main thread accepts connection
    → Spawns handle_client thread for Alice
    
    4. Alice's handler thread sends: "Enter your username: "
    
    5. Alice types: "Alice"
    Client sends → Server receives
    
    6. Server validates username, adds to clients list:
    clients.append({'socket': alice_socket, 'username': 'Alice', ...})
    
    7. Server broadcasts to all others: "[14:32] Alice joined the chat"
    → Bob and Charlie's clients receive and display it
    
    8. Server sends to Alice: "[14:32] Welcome to the chat, Alice!"
    ```

    ### **Scenario 2: User Sends Message**
    ```
    1. Alice types in client: "Hello everyone!"
    
    2. Client sends to server → Alice's handler thread receives
    
    3. Handler validates:
    - Not empty ✓
    - Under 500 chars ✓
    
    4. Handler adds timestamp: "[14:35] Alice: Hello everyone!"
    
    5. Handler calls broadcast(message, sender_socket=alice_socket)
    
    6. Broadcast function:
    - Acquires clients_lock
    - Loops through clients list
    - Sends to Bob's socket ✓
    - Sends to Charlie's socket ✓
    - Skips Alice's socket (sender)
    - Releases lock
    
    7. Bob and Charlie's clients receive and display:
    "[14:35] Alice: Hello everyone!"
    ```

    ### **Scenario 3: User Leaves**
    ```
    1. Alice presses Ctrl+C in client
    
    2. Client closes socket connection
    
    3. Alice's handler thread detects:
    - socket.recv() returns empty bytes
    
    4. Handler cleanup:
    - Acquires clients_lock
    - Removes Alice from clients list
    - Releases lock
    
    5. Handler broadcasts: "[14:40] Alice left the chat"
    → Bob and Charlie receive notification
    
    6. Handler closes socket and thread exits
    ```

    ---

    ## Thread Safety - Critical Sections

    **Shared Resource:** `clients` list

    **Race Condition Example:**
    ```
    Thread A (Bob's handler) trying to broadcast while
    Thread B (Charlie's handler) is removing disconnected user
    → Could access modified list mid-iteration = CRASH
    ```

Solution: Using threading.lock()
- ```Python
  with clients_lock:
    # Safe to read/modify clients list
    for client in clients:
        client['socket'].send(message)
    ```

    **Where locks are needed:**
    - Adding client to list (on join)
    - Removing client from list (on leave)
    - Iterating clients for broadcast
    - Checking username uniqueness

    ---

    ## File Structure
    
    chat-server/
    │
    ├── server.py          # Main server with threading
    ├── client.py          # Terminal client
    ├── requirements.txt   # (empty for now, just uses stdlib)
    └── README.md          # How to run
    ```


## Error Handling
- Server Side
    - Client disconnects abruptly: Handler catches empty recv(), cleans up gracefully
    - Send fails(broken pipe): Catch exception, mark client for removal, continue
    - Invalid Username: Send error message, re-prompt
    - Empty message: Ignore siletently
    - Message too long: Rejet message and tell user its too long of a message
    - Server Shutdown: Catch KeyboardInterrupt, broadcast shutdown message, close all sockets
- Client Side:
    - Connetion Refused: Print error, exit gracefully
    - Server disconnects: Stop recevied thread, notify user, exit


## Testing Strategies
- Manual Tests
    - Phase 1: Server Startup
        - Start server with python server.py
        - Verify console shows: "Server listening on localhost:8888"
        - Check server doesn't crash on startup
        - Verify can stop server cleanly with Ctrl+C

    - Phase 2: Single Client Connection
        - Connect one client: python client.py
        - Verify prompted for username
        - Enter username, verify welcome message received
        - Send a message, verify it's echoed back with timestamp
        - Disconnect client (Ctrl+C), verify clean exit
        - Check server still running after client disconnects

    - Phase 3: Multiple Clients (Core Functionality)
        - Connect Client 1 (Alice), enter username
        - Connect Client 2 (Bob), verify Alice sees "Bob joined the chat"
        - Bob sends message, verify Alice receives it
        - Alice sends message, verify Bob receives it
        - Connect Client 3 (Charlie), verify Alice and Bob both see join notification
        - Charlie sends message, verify both Alice and Bob receive it
        - Verify each user sees their own messages echoed back with timestamp

## System Health Checks
- Check for resource leaks
    ``` Python
    # Check number of open file descriptors for server process
    # Should be roughly: 1 listening socket + 1 per connected client + ~20 overhead
    lsof -p $(pgrep -f server.py) | wc -l

    # Before connecting clients: ~25
    # With 3 clients: ~28
    # After clients disconnect: should return to ~25
  ```
- Check for Zombie threads
    ``` Python
    # View all threads for server process
    ps -eLf | grep server.py

    # Should see: 1 main thread + 1 thread per connected client
    # After clients disconnect, thread count should decrease
    ```
- Check Socket Status
  ``` Python
  # Verify server is listening on correct port
    lsof -i :8888

  # Should show:
  # COMMAND   PID  USER   FD   TYPE  DEVICE  SIZE/OFF  NODE  NAME
  # python    1234 user   3u   IPv4  0x...   0t0       TCP   *:8888 (LISTEN)
  ```
- Check for Port Binding Issues
    ``` Python
    # See what's using port 8888 (if server won't start)
    lsof -i :8888

    # Kill any lingering processes
    kill -9 $(lsof -t -i:8888)
    ```


