import tkinter as tk
from tkinter import filedialog, messagebox
import os
import sys
import re
from datetime import datetime, timezone

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class FileMonitorApp:
       
    def __init__(self, root):
        self.root = root
        self.root.title("Star Citizen Kill Logger 3000")
        self.root.iconbitmap(resource_path("logger_iconfile.ico"))  # Set custom window icon
        self.file_path = None
        self.last_modified = 0
        self.player_name = "Unknown"

        # GUI Elements
        self.frame = tk.Frame(root, padx=10, pady=10)
        self.frame.pack(fill="both", expand=True)
        self.auto_scroll_enabled = True

        self.player_label = tk.Label(self.frame, text=f"Player Name: {self.player_name}", font=("Arial", 12, "bold"))
        self.player_label.pack(anchor="w")

        # Filters + Button Row
        self.filter_frame = tk.Frame(self.frame)
        self.filter_frame.pack(fill="x", pady=(0, 10))

        self.show_player_kills = tk.BooleanVar(value=True)
        self.show_other_kills = tk.BooleanVar(value=True)

        self.player_kills_checkbox = tk.Checkbutton(
            self.filter_frame, text="Show Player Kills",
            variable=self.show_player_kills, command=self.update_display
        )
        self.player_kills_checkbox.pack(side="left")

        self.other_kills_checkbox = tk.Checkbutton(
            self.filter_frame, text="Show Other Kills",
            variable=self.show_other_kills, command=self.update_display
        )
        self.other_kills_checkbox.pack(side="left", padx=(10, 0))

        # Right-aligned button
        self.open_button = tk.Button(self.filter_frame, text="Find Game.log", command=self.open_file)
        self.open_button.pack(side="right")


        # Scrollable Text Area
        self.text_frame = tk.Frame(self.frame)
        self.text_frame.pack(fill="both", expand=True)

        self.text_widget = tk.Text(self.text_frame, wrap="word", height=25, width=70)
        self.text_widget.pack(side="left", fill="both", expand=True)

        self.scrollbar = tk.Scrollbar(self.text_frame, command=self.text_widget.yview)
        self.scrollbar.pack(side="right", fill="y")

        self.text_widget.config(yscrollcommand=self.scrollbar.set)

        # Color tags
        self.text_widget.tag_configure("player_kill", foreground="green")
        self.text_widget.tag_configure("other_kill", foreground="red")
        
        #scroll event detection for auto-pausing scroll later on
        self.text_widget.bind("<MouseWheel>", self.on_scroll)
        self.text_widget.bind("<Button-4>", self.on_scroll)  # Linux scroll up
        self.text_widget.bind("<Button-5>", self.on_scroll)  # Linux scroll down
        self.text_widget.bind("<Key>", self.on_scroll)       # In case of keyboard scroll
        self.text_widget.bind("<ButtonRelease-1>", self.on_scroll)
        
        #Auto open the gamelog dialog box
        self.open_file()

    #scroll detection
    def on_scroll(self, event=None):
        # Get current view position: returns a tuple like (first_visible, last_visible)
        first, last = self.text_widget.yview()
        # If last is < 1.0, user is not at the bottom
        self.auto_scroll_enabled = last >= 0.999



    def open_file(self):
        path = filedialog.askopenfilename(
            title="Please locate your Game.log",
            initialfile="game.log",
            filetypes=(("Log files", "*.log"), ("All files", "*.*"))
        )
        if path:
            self.file_path = path
            self.last_modified = 0
            self.monitor_file()

    def monitor_file(self):
        if self.file_path and os.path.exists(self.file_path):
            modified_time = os.path.getmtime(self.file_path)
            if modified_time != self.last_modified:
                self.last_modified = modified_time
                self.update_display()
        self.root.after(1000, self.monitor_file)

    def parse_timestamp(self, line):
        timestamp_match = re.match(r"<(?P<timestamp>[\d\-T:\.]+)Z>", line)
        if timestamp_match:
            try:
                utc_time = datetime.strptime(timestamp_match.group("timestamp"), "%Y-%m-%dT%H:%M:%S.%f")
                local_time = utc_time.replace(tzinfo=timezone.utc).astimezone()
                return local_time.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                return "InvalidTime"
        return "UnknownTime"

    def extract_player_name(self, line):
        match = re.search(r"name (?P<name>\w+)", line)
        if match:
            new_name = match.group("name")
            if new_name != self.player_name:
                self.player_name = new_name
                self.player_label.config(text=f"Player Name: {self.player_name}")

    def extract_clean_vehicle_name(self, raw_name):
        match = re.match(r"(?:[A-Z]+_)?(?P<name>[A-Za-z]+)(?:_\d+)?", raw_name)
        if match:
            return match.group("name")
        return raw_name

    #use this to get our position for freezing the window when we're not autoscrolling
    def line_to_fraction(self, line_num):
        total_lines = int(self.text_widget.index("end-1c").split('.')[0])
        if total_lines == 0:
            return 0.0
        return line_num / total_lines


    def update_display(self):
        try:
            with open(self.file_path, 'r') as file:
                lines = file.readlines()
                
                # Get top visible line before update
                visible_index = self.text_widget.index("@0,0")
                visible_line = int(visible_index.split('.')[0])

                # Check if user is at the bottom before clearing/updating
                yview = self.text_widget.yview()
                user_was_at_bottom = yview[1] >= 0.999

                # Save current view position if not at bottom
                if not user_was_at_bottom:
                    current_index = self.text_widget.index("@0,0")

                self.text_widget.config(state="normal")
                self.text_widget.delete("1.0", tk.END)

                for line in lines:
                    if "<AccountLoginCharacterStatus_Character>" in line:
                        self.extract_player_name(line)

                    elif "<Actor Death>" in line:
                        timestamp = self.parse_timestamp(line)
                        match = re.search(
                            r"'(?P<killed>[^']+)' \[\d+\].*?killed by '(?P<killer>[^']+)' \[\d+\].*?with damage type '(?P<dmg>[^']+)'",
                            line
                        )
                        if match:
                            killed = match.group("killed")
                            killer = match.group("killer")
                            if killed.startswith("PU_Pilots-Human"):
                                killed = "Human NPC"
                            dmg_type = match.group("dmg")
                            output_line = f"{timestamp} - {killer} >> {killed} with {dmg_type}\n"
                            is_player = (killer == self.player_name)

                            if is_player and self.show_player_kills.get():
                                self.text_widget.insert(tk.END, output_line, "player_kill")
                            elif not is_player and self.show_other_kills.get():
                                self.text_widget.insert(tk.END, output_line, "other_kill")

                    elif "<Vehicle Destruction>" in line:
                        timestamp = self.parse_timestamp(line)
                        match = re.search(
                            r"Vehicle '(?P<vehicle>[^']+)'.*?destroy level (?P<from_level>\d) to (?P<to_level>\d).*?caused by '(?P<causer>[^']+)'",
                            line
                        )
                        if match:
                            raw_vehicle = match.group("vehicle")
                            vehicle_name = self.extract_clean_vehicle_name(raw_vehicle)
                            from_level = int(match.group("from_level"))
                            to_level = int(match.group("to_level"))
                            causer = match.group("causer")

                            if from_level == 0 and to_level == 1:
                                kill_type = f"Soft Kill ({vehicle_name})"
                            elif (from_level == 1 and to_level == 2) or (from_level == 0 and to_level == 2):
                                kill_type = f"Hard Kill ({vehicle_name})"
                            else:
                                kill_type = f"Unknown Kill Type ({from_level}->{to_level}) ({vehicle_name})"

                            output_line = f"{timestamp} - {causer} >> {kill_type}\n"
                            is_player = (causer == self.player_name)

                            if is_player and self.show_player_kills.get():
                                self.text_widget.insert(tk.END, output_line, "player_kill")
                            elif not is_player and self.show_other_kills.get():
                                self.text_widget.insert(tk.END, output_line, "other_kill")

                self.text_widget.config(state="disabled")

                # Restore position or scroll to bottom
                if user_was_at_bottom:
                    self.text_widget.see(tk.END)
                else:
                    self.text_widget.yview_moveto(self.line_to_fraction(visible_line - 1)) #restore previous scroll position

        except Exception as e:
            messagebox.showerror("Error", f"Could not read file:\n{e}")


# Run the app
if __name__ == "__main__":
    root = tk.Tk()
    app = FileMonitorApp(root)
    root.mainloop()
