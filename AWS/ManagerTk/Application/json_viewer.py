import tkinter as tk
from tkinter import ttk
import json
#https://www.w3resource.com/python-exercises/tkinter/python-tkinter-file-operations-and-integration-exercise-4.php
class JSONViewer:
    def __init__(self, root,text,title):
        self.root = root
        self.root.title("JSON Viewer " + title)

        # Create a Frame for displaying JSON data
        self.frame = ttk.Frame(root)
        self.frame.pack(padx=20, pady=20, fill=tk.BOTH, expand=True)

        # Create a Text widget for displaying JSON content
        self.text_widget = tk.Text(self.frame, wrap=tk.WORD)
        self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Create a Scrollbar for the Text widget
        self.scrollbar = ttk.Scrollbar(self.frame, command=self.text_widget.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_widget.config(yscrollcommand=self.scrollbar.set)

        # Load and display JSON data
        self.load_json_data(text)  # Replace with your JSON file path

    def load_json_data(self, text ): #json_file
        try:
            # Load JSON data from the file
            #with open(json_file, "r") as file:
            #    data = json.load(file)
            
            data = json.loads(text)
            # Format JSON data as a string and display it in the Text widget
            formatted_json = json.dumps(data, indent=4)
            self.text_widget.insert(tk.END, formatted_json)

            # Make the Text widget read-only
            self.text_widget.config(state=tk.DISABLED)

        except FileNotFoundError:
            self.text_widget.insert(tk.END, "File not found.")
            self.text_widget.config(state=tk.DISABLED)

if __name__ == "__main__":
    root = tk.Tk()
    app = JSONViewer(root, '{"name": "Alberto", "age": 24, "city": "New York"}' ,"example")
    root.mainloop()