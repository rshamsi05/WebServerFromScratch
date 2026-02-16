import socket
import threading
import sys

class ChatClient:
    def __init__(self, host='localhost', port=8888):
        self.host=host
        self.port=port
        self.socket = None
        self.username = ""
        self.running = False
    
    def connect(self):
        '''
        Connect to the chat server
        '''
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.running = True
            print(f"Connected to chat server at {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"Unable to connect to server: {e}")
            return False

    def receive_messages(self):
        '''
        Continously receive messages from the server and print them
        '''
        while(self.running):
            try:
                message = self.socket.recv(1024).decode('utf-8')
                if(message):
                    print(message)
                else:
                    # Server has disconnected
                    break
            except Exception as e:
                if(self.running):
                    print(f"Error receiving message: {e}")
                break
        self.running = False
        self.socket.close()
    
    def send_messages(self):
        '''
        read user input from terminal and send to server
        '''
        try:
            username = input("Enter your username: ").strip()
            if(not username):
                print("Username cannot be empty.")
                self.running = False
                self.socket.close()
                return

            self.username = username
            self.socket.send(username.encode('utf-8'))

            # Read user input and send to server
            while(self.running):
                message = input()

                # check to see that the client is still running(in case receive thread closed it)
                if(not self.running):
                    break

                try:
                    self.socket.send(message.encode('utf-8'))
                except Exception as e:
                    print(f"Error sending message: {e}")
                    break
        except KeyboardInterrupt:
            print("\n Disconnecting from server.")
        except Exception as e:
            print(f"Error: {e}")
        
        self.running = False
        self.socket.close()
    
    def start(self):
        '''
        Starting the client
        '''
        if(not self.connect()):
            return

        # start a thread to receive messages from the server
        receive_thread = threading.Thread(target=self.receive_messages)
        receive_thread.daemon = True
        receive_thread.start()

        # use main thread for sending messages
        self.send_messages()

def main():
    '''
    Entry point for the client
    '''
    client = ChatClient()
    try:
        client.start()
    except KeyboardInterrupt:
        print("\nClient shutting down.")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        print("Disconnecting from server.")


if __name__ == "__main__":
    main()
