import tkinter as tk
from tkinter import scrolledtext, ttk
import json
import socket
import threading

class ModernScrollbar(tk.Canvas):
    def __init__(self, parent, **kwargs):
        self.command = kwargs.pop('command', None)
        kwargs['width'] = kwargs.get('width', 4)  # Make it thinner
        kwargs['highlightthickness'] = 0
        kwargs['bd'] = 0
        tk.Canvas.__init__(self, parent, **kwargs)
        self._thumb_color = '#202225'
        self._trough_color = '#2f3136'
        self.hover = False
        self.bind('<Enter>', self.on_enter)
        self.bind('<Leave>', self.on_leave)
        self.bind('<ButtonPress-1>', self.on_press)
        self.bind('<ButtonRelease-1>', self.on_release)
        self.bind('<B1-Motion>', self.on_move)
        self.redraw(0, 1)

    def set_colors(self, thumb_color, trough_color):
        self._thumb_color = thumb_color
        self._trough_color = trough_color
        self.redraw(self.first, self.last)

    def redraw(self, first, last):
        self.delete('all')
        self.create_rectangle(0, 0, self.winfo_width(), self.winfo_height(), fill=self._trough_color, width=0)
        height = self.winfo_height()
        top = int(height * first)
        bottom = int(height * last)
        if self.hover or hasattr(self, 'y'):
            self.create_rectangle(0, top, self.winfo_width(), bottom, fill=self._thumb_color, width=0)
        self.first = first
        self.last = last

    def set(self, first, last):
        self.redraw(float(first), float(last))

    def on_enter(self, event):
        self.hover = True
        self.redraw(self.first, self.last)

    def on_leave(self, event):
        self.hover = False
        self.redraw(self.first, self.last)

    def on_press(self, event):
        self.y = event.y
        self.redraw(self.first, self.last)

    def on_release(self, event):
        self.y = None
        self.redraw(self.first, self.last)

    def on_move(self, event):
        if self.y is None:
            return
        delta = event.y - self.y
        if self.command:
            self.command('moveto', delta / self.winfo_height())
        self.y = event.y

class MessagingClientGUI:
    def __init__(self, master):
        # Initialize the main window
        self.master = master
        master.title("Discord Message Client for Bots")
        master.geometry("600x400")
        master.minsize(300, 200)  # Set minimum size
        master.overrideredirect(True)  # Remove default title bar for custom styling
        
        # Configure grid layout for responsive design
        master.grid_columnconfigure(0, weight=1)
        master.grid_rowconfigure(1, weight=1)

        # Define color schemes for dark and light modes
        self.dark_mode = {
            "bg": "#36393f",
            "fg": "#ffffff",
            "input_bg": "#40444b",
            "scroll_bg": "#2f3136",
            "scroll_thumb": "#202225",
            "title_bg": "#202225"
        }
        self.light_mode = {
            "bg": "#ffffff",
            "fg": "#000000",
            "input_bg": "#f0f0f0",
            "scroll_bg": "#e0e0e0",
            "scroll_thumb": "#c0c0c0",
            "title_bg": "#e0e0e0"
        }
        self.current_mode = self.dark_mode  # Start with dark mode

        # Create custom title bar for a unique look
        self.title_bar = tk.Frame(master, bg=self.current_mode["title_bg"], relief='raised', bd=0, height=30)
        self.title_bar.grid(row=0, column=0, columnspan=3, sticky="ew")
        self.title_bar.grid_columnconfigure(0, weight=1)
        self.title_bar.grid_propagate(False)  # Prevent the title bar from resizing

        self.title_label = tk.Label(self.title_bar, text="Discord Message Client for Bots", 
                                    bg=self.current_mode["title_bg"], fg=self.current_mode["fg"])
        self.title_label.grid(row=0, column=0, padx=5, sticky="w")

        self.mode_button = tk.Button(self.title_bar, text="🌙", command=self.toggle_mode, 
                                     font=("Arial", 12), width=3, height=1)
        self.mode_button.grid(row=0, column=1, padx=(0, 5))

        self.close_button = tk.Button(self.title_bar, text="×", command=self.master.quit, 
                                      bg=self.current_mode["title_bg"], fg=self.current_mode["fg"],
                                      relief="flat", activebackground="red", activeforeground="white",
                                      width=3, height=1)
        self.close_button.grid(row=0, column=2)

        # Make window draggable by binding mouse events to the title bar
        self.title_bar.bind('<Button-1>', self.start_move)
        self.title_bar.bind('<ButtonRelease-1>', self.stop_move)
        self.title_bar.bind('<B1-Motion>', self.do_move)

        # Create main content frame
        self.content_frame = tk.Frame(master, bg=self.current_mode["bg"])
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)

        # Create output area for displaying messages
        self.output_frame = tk.Frame(self.content_frame, bg=self.current_mode["bg"])
        self.output_frame.grid(row=0, column=0, sticky="nsew")
        self.output_frame.grid_columnconfigure(0, weight=1)
        self.output_frame.grid_rowconfigure(0, weight=1)

        self.output_area = tk.Text(self.output_frame, wrap=tk.WORD, state=tk.DISABLED, bd=0, highlightthickness=0)
        self.output_area.grid(row=0, column=0, sticky="nsew")

        self.output_scrollbar = ModernScrollbar(self.output_frame, command=self.output_area.yview)
        self.output_scrollbar.grid(row=0, column=1, sticky="ns")  # Changed from "nse" to "ns"
        self.output_area.configure(yscrollcommand=self.output_scrollbar.set)

        # Create input area for typing messages
        self.input_frame = tk.Frame(self.content_frame, bg=self.current_mode["bg"])
        self.input_frame.grid(row=1, column=0, sticky="ew", pady=(5, 0))
        self.input_frame.grid_columnconfigure(0, weight=1)

        self.input_area = tk.Text(self.input_frame, wrap=tk.WORD, height=3, bd=0, highlightthickness=0)
        self.input_area.grid(row=0, column=0, sticky="ew")
        self.input_area.bind("<Shift-Return>", self.on_shift_enter)
        self.input_area.bind("<FocusIn>", self.on_entry_click)
        self.input_area.bind("<FocusOut>", self.on_focusout)
        self.input_area.bind("<Key>", self.on_key_press)

        # Add placeholder text to input area
        self.placeholder_text = "[Channel ID] [Message] e.g. 432789347289 This is an example"
        self.input_area.insert("1.0", self.placeholder_text)
        self.input_area.config(fg="grey")

        self.input_scrollbar = ModernScrollbar(self.input_frame, command=self.input_area.yview)
        self.input_scrollbar.grid(row=0, column=1, sticky="ns")  # Changed from "nse" to "ns"
        self.input_area.configure(yscrollcommand=self.input_scrollbar.set)

        # Create send button
        self.send_button = tk.Button(self.input_frame, text="Send", command=self.send_message,
                                     bg="#4CAF50", fg="white", 
                                     activebackground="#45a049", activeforeground="white",
                                     relief=tk.FLAT, padx=10, pady=5,
                                     font=("Arial", 10, "bold"))
        self.send_button.grid(row=0, column=2, padx=(5, 0))

        # Apply initial color scheme
        self.apply_color_scheme()

        # Bind events for updating scrollbar sizes
        self.output_area.bind("<Configure>", self.update_output_scrollbar)
        self.input_area.bind("<Configure>", self.update_input_scrollbar)

        # Initialize network-related attributes
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connected = False

        # Start the connection process in a separate thread
        threading.Thread(target=self.connect_to_server, daemon=True).start()

    def connect_to_server(self):
        # Attempt to connect to the server
        host = 'localhost'
        port = 3000

        self.log_message("Connecting to the bot messaging server...")
        try:
            self.client.connect((host, port))
            self.connected = True
            self.log_message("Connected!")
            self.receive_messages()
        except Exception as e:
            self.log_message(f"Connection Error: {e}")

    def receive_messages(self):
        # Continuously receive and process messages from the server
        while self.connected:
            try:
                data = self.client.recv(1024).decode('utf-8')
                if not data:
                    break
                response = json.loads(data)
                if 'message' in response:
                    self.log_message(f"Server: {response['message']}")
                else:
                    self.log_message(f"Received from server: {data}")
            except json.JSONDecodeError:
                self.log_message(f"Received non-JSON data: {data}")
            except Exception as e:
                self.log_message(f"Error receiving message: {e}")
                break
        self.connected = False
        self.log_message("Connection closed")

    def send_message(self):
        # Send a message to the server
        if not self.connected:
            self.log_message("Not connected to server")
            return

        message = self.input_area.get("1.0", tk.END).strip()
        if not message or message == self.placeholder_text:
            return

        try:
            channel_id, content = message.split(' ', 1)
            data = json.dumps({"channelId": channel_id, "content": content})
            self.client.send(data.encode('utf-8'))
            self.log_message(f"Sending message: {data}")
            self.input_area.delete("1.0", tk.END)
            self.on_focusout(None)  # Re-add placeholder text
        except ValueError:
            self.log_message("Invalid input. Please provide both channel ID and message.")

    def on_shift_enter(self, event):
        self.input_area.insert(tk.INSERT, '\n')
        return 'break'

    def log_message(self, message):
        # Display a message in the output area
        self.output_area.config(state=tk.NORMAL)
        self.output_area.insert(tk.END, message + '\n')
        self.output_area.see(tk.END)
        self.output_area.config(state=tk.DISABLED)

    def toggle_mode(self):
        # Switch between light and dark modes
        if self.current_mode == self.light_mode:
            self.current_mode = self.dark_mode
            self.mode_button.config(text="🌙")  # Moon emoji for dark mode
        else:
            self.current_mode = self.light_mode
            self.mode_button.config(text="🔆")  # Sun emoji for light mode
        self.apply_color_scheme()

    def apply_color_scheme(self):
        # Apply the current color scheme to all UI elements
        self.master.configure(bg=self.current_mode["bg"])
        self.title_bar.config(bg=self.current_mode["title_bg"])
        self.title_label.config(bg=self.current_mode["title_bg"], fg=self.current_mode["fg"])
        self.close_button.config(bg=self.current_mode["title_bg"], fg=self.current_mode["fg"])
        self.mode_button.config(bg=self.current_mode["bg"], fg=self.current_mode["fg"])
        self.output_area.config(bg=self.current_mode["bg"], fg=self.current_mode["fg"])
        self.input_area.config(bg=self.current_mode["input_bg"], fg=self.current_mode["fg"])
        self.content_frame.config(bg=self.current_mode["bg"])
        self.input_frame.config(bg=self.current_mode["bg"])
        self.output_frame.config(bg=self.current_mode["bg"])
        
        self.output_scrollbar.set_colors(self.current_mode["scroll_thumb"], self.current_mode["scroll_bg"])
        self.input_scrollbar.set_colors(self.current_mode["scroll_thumb"], self.current_mode["scroll_bg"])

        if self.current_mode == self.dark_mode:
            self.send_button.config(bg="#4CAF50", fg="white", activebackground="#45a049", activeforeground="white")
        else:
            self.send_button.config(bg="#4CAF50", fg="white", activebackground="#45a049", activeforeground="white")

        if self.input_area.get("1.0", "end-1c") == self.placeholder_text:
            self.input_area.config(fg="grey")

    def start_move(self, event):
        # Start window dragging
        self.x = event.x
        self.y = event.y

    def stop_move(self, event):
        # Stop window dragging
        self.x = None
        self.y = None

    def do_move(self, event):
        # Perform window dragging
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.master.winfo_x() + deltax
        y = self.master.winfo_y() + deltay
        self.master.geometry(f"+{x}+{y}")

    def update_output_scrollbar(self, event):
        # Update the height of the output scrollbar
        self.output_scrollbar.configure(height=event.height)

    def update_input_scrollbar(self, event):
        # Update the height of the input scrollbar
        self.input_scrollbar.configure(height=event.height)

    def on_entry_click(self, event):
        # Handle click event on the input area
        # Remove placeholder text when clicked
        if self.input_area.get("1.0", "end-1c") == self.placeholder_text:
            self.input_area.delete("1.0", tk.END)
            self.input_area.config(fg=self.current_mode["fg"])

    def on_focusout(self, event):
        # Handle focus out event on the input area
        # Restore placeholder text if empty
        if self.input_area.get("1.0", "end-1c") == "":
            self.input_area.insert("1.0", self.placeholder_text)
            self.input_area.config(fg="grey")

    def on_key_press(self, event):
        # Handle key press event in the input area
        # Remove placeholder text when typing starts
        if self.input_area.get("1.0", "end-1c") == self.placeholder_text:
            self.input_area.delete("1.0", tk.END)
            self.input_area.config(fg=self.current_mode["fg"])

# Main
if __name__ == "__main__":
    root = tk.Tk()
    app = MessagingClientGUI(root)
    root.mainloop()
