import socket
import threading
import time

from datetime import datetime

# State variables
clients = [] # List of connected clients
clients_lock = threading.Lock() # thread lock to prevent race conditions when accessing client list

def broadcast(message, sender_socket=None):
    '''
    Args:
        message: String to send to all clients
        sender_socket: Socket to exclude(sender of the message)
    '''
    with clients_lock:
        for client in clients[:]: # Create copy to avoid modification during iteration
            if(client['socket'] != sender_socket):
                try:
                    client['socket'].send(message.encode('utf-8'))
                except:
                    # if send fails, remove the client
                    print(f"Removing client {client['username']} due to connection issue")
                    clients.remove(client)

# TODO: figure out a way later on to debloat this function
def handle_client(client_socket, address):
    '''
    Handles client connection for a single client in a separate thread
    '''
    try:
        # Prompt client for username
        client_socket.send("Enter your username: ".encode('utf-8'))
        username = client_socket.recv(1024).decode('utf-8').strip()

        # Validate username
        if(not username):
            client_socket.send("Username cannot be empty. Disconnecting.\n".encode('utf-8'))
            client_socket.close()
            return

        # Adding client info the list of clients
        client_info = {
            'socket': client_socket,
            'username': username,
            'address': address,
            'connected_at': datetime.now()
        }

        # using client_lock to add client to the list of clients
        with clients_lock:
            clients.append(client_info)
        

        # Create and send join notification messsage to all other clients
        joinMessage = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {username} has joined the chat."
        print(joinMessage)
        # TODO: Ask why we dont we need to pass in the client_socket when broadcasting the join message, but we do for the regular messages
        broadcast(joinMessage)

        # Secnd welcome message
        welcomeMsg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Welcome to the chat, {username}!"
        client_socket.send(welcomeMsg.encode('utf-8'))

        # Logic to handle message from client
        while(True):
            try:
                message = client_socket.recv(1024).decode('utf-8').strip()
                # if messasge is empty the client has disconnected
                if(not message):
                    break
                
                # Checks to see if the message is too long, if it is, send error message to client and skip broadcasting
                if(len(message) > 500):
                    client_socket.send("Message is too long, Max character limit is 500.\n".encode('utf-8'))
                    continue
                # format message with timestamp and username
                formattedMsg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {username}: {message}"
                print(formattedMsg)

                #Broadcast formatted to all other clients
                broadcast(formattedMsg, sender_socket=client_socket)
            except:
                # If exception occurs, client has likely disconnected
                # TODO: Ask if we can make these exceptions more specific and if there are other cases for which excpetion are thrown.
                break
    except Exception as e:
        # Handles unexpected errors during client handling
        print(f"Error handling client {address}: {e}")

    finally:
        # Cleanup code that runs regardless of how the rest of the function flows
        try:
            # Remove client from shared clients list
            usernameRemoved = None
            with clients_lock:
                # Find and remove client from the shared client list
                for i, client in enumerate(clients):
                    if(client['socket'] == client_socket):
                        clients.pop(i)
                        usernameRemoved = client['username']
                        break            
            
            if(usernameRemoved):
                # Broadcast leave message to other clients
                leave_message = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {usernameRemoved} has left the chat."
                print(leave_message)
                broadcast(leave_message)

            # Close client socket
            client_socket.close()
        except Exception as e:
            print(f"Error during cleanup for client {address}: {e}")



def start_server():
    '''
    Initialize and start the chat server
    '''

    # Sever host and port initialization
    host='localhost'
    port = 8888


    # IPv4 TCP socket creation
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Applying socket options
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        # Bind socket to host and port
        server.bind((host, port))

        # Start listening for incoming connections
        server.listen()
        print(f"Chat server started on {host}:{port}")

        # Main loop to accept incoming client connections
        while(True):
            try:
                # Accept new client
                client_socket, address = server.accept()
                print(f"New connection from {address}")


                # Create new thread to handle client for concurrent handling
                client_thread = threading.Thread(
                    target=handle_client,
                    args=(client_socket, address)
                )

                # Set thread to dameon(daemon threads die when the program ends)
                client_thread.daemon = True

                # Start client thread
                client_thread.start()
            # Exeption refers to the terminal version of the chat room
            except KeyboardInterrupt:
                # Graceful shutdown on Ctrl+C
                print(f"\n Shutting down server...")
                break
            except Exception as e:
                # TODO: Ask if we can make these exceptions more specific and if there are other cases for which excpetion are thrown.
                # Handle other unexpected exceptions during connection acceptance
                print(f"Error accepting connection: {e}")
    finally:
        # Close server socket when shutting down
        server.close()
        print("Server shut down.")

# Entry point for the program
if __name__ == "__main__":
    # Start server
    start_server()
