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
        self.show_misc_kills = tk.BooleanVar(value=True)  # New filter for kills that don't involve the player

        # Player kills
        self.player_kills_checkbox = tk.Checkbutton(
            self.filter_frame, text="Show Player Kills",
            variable=self.show_player_kills, command=self.update_display
        )
        self.player_kills_checkbox.pack(side="left")

        # Player GETTING killed
        self.other_kills_checkbox = tk.Checkbutton(
            self.filter_frame, text="Show Player Deaths",
            variable=self.show_other_kills, command=self.update_display
        )
        self.other_kills_checkbox.pack(side="left", padx=(10, 0))

        # Random kills not involving player
        self.misc_kills_checkbox = tk.Checkbutton(
        self.filter_frame, text="Show Other Kills",
        variable=self.show_misc_kills, command=self.update_display
        )
        self.misc_kills_checkbox.pack(side="left", padx=(10, 0))


        # Right-aligned button
        self.open_button = tk.Button(self.filter_frame, text="Find Game.log", command=self.open_file)
        self.open_button.pack(side="right")

        # Dark Mode toggle button
        self.dark_mode = False
        self.dark_mode_button = tk.Button(self.filter_frame, text="Toggle Dark Mode", command=self.toggle_dark_mode)
        self.dark_mode_button.pack(side="right", padx=(0, 10))

        

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
        self.text_widget.tag_configure("player_death", foreground="red")
        self.text_widget.tag_configure("other_kill", foreground="orange")  # orange for others
        
        #scroll event detection for auto-pausing scroll later on
        self.text_widget.bind("<MouseWheel>", self.on_scroll)
        self.text_widget.bind("<Button-4>", self.on_scroll)  # Linux scroll up
        self.text_widget.bind("<Button-5>", self.on_scroll)  # Linux scroll down
        self.text_widget.bind("<Key>", self.on_scroll)       # In case of keyboard scroll
        self.text_widget.bind("<ButtonRelease-1>", self.on_scroll)
        
        #Auto open the gamelog dialog box
        self.open_file()

    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode

        # Define dark and light theme colors
        bg_color = "#2e2e2e" if self.dark_mode else "SystemButtonFace"
        text_bg = "black" if self.dark_mode else "white"
        text_fg = "white" if self.dark_mode else "black"
        checkbox_bg = bg_color
        checkbox_active_bg = "#3e3e3e" if self.dark_mode else "SystemButtonFace"
        scrollbar_bg = "#444444" if self.dark_mode else "SystemButtonFace"
        scrollbar_trough = "#2a2a2a" if self.dark_mode else "SystemButtonFace"

        # Apply background to main containers
        self.root.configure(bg=bg_color)
        self.frame.configure(bg=bg_color)
        self.filter_frame.configure(bg=bg_color)
        self.text_frame.configure(bg=bg_color)

        # Update text widget
        self.text_widget.configure(
            bg=text_bg,
            fg=text_fg,
            insertbackground=text_fg,
            selectbackground="#555555" if self.dark_mode else "#cceeff"
        )

        # Update labels and buttons
        widgets = [
            self.player_label,
            self.open_button,
            self.dark_mode_button
        ]
        for widget in widgets:
            widget.configure(bg=bg_color, fg=text_fg)

        # Update checkboxes
        self.player_kills_checkbox.configure(
            bg=checkbox_bg, fg=text_fg, activebackground=checkbox_active_bg, selectcolor=bg_color
        )
        self.other_kills_checkbox.configure(
            bg=checkbox_bg, fg=text_fg, activebackground=checkbox_active_bg, selectcolor=bg_color
        )
        self.misc_kills_checkbox.configure(
            bg=checkbox_bg, fg=text_fg, activebackground=checkbox_active_bg, selectcolor=bg_color
        )

        # Update scrollbar appearance (color change is limited in native Tkinter, but we can try)
        try:
            self.scrollbar.configure(
                troughcolor=scrollbar_trough,
                background=scrollbar_bg,
                activebackground=scrollbar_bg
            )
        except tk.TclError:
            # Some themes don't support custom scrollbar styling, so we skip it
            pass



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
        import re

        # Check for a valid manufacturer prefix (2 to 4 uppercase letters followed by underscore)
        if re.match(r"^[A-Z]{2,4}_", raw_name):
            # This is a ship: remove prefix, strip trailing numbers, and remove underscores
            parts = raw_name.split("_")
            clean_parts = parts[1:-1] if parts[-1].isdigit() else parts[1:]
            name = " ".join(clean_parts)
        else:
            # Not a ship: truncate everything after the first underscore
            base = raw_name.split("_")[0]

            # Insert a space before each capital letter after the first
            name = re.sub(r'(?<!^)([A-Z])', r' \1', base)

        # Handle PU AI tag logic
        if "PU AI" in name:
            name = re.sub(r"\bPU AI.*", "", name).strip()
            name = f"NPC {name}"

        return name




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
                            dmg_type = match.group("dmg")

                            if killed.startswith("PU_Pilots-Human"):
                                killed = "Human NPC"

                            output_line = f"{timestamp} - {killer} >> {killed} with {dmg_type}\n"

                            # Determine tag
                            if killer == self.player_name:
                                tag = "player_kill"
                            elif killed == self.player_name:
                                tag = "player_death"
                            else:
                                tag = "other_kill"

                            # Show based on filters
                            if (
                                (tag == "player_kill" and self.show_player_kills.get()) or
                                (tag == "player_death" and self.show_other_kills.get()) or
                                (tag == "other_kill" and self.show_misc_kills.get())
                            ):
                                self.text_widget.insert(tk.END, output_line, tag)


                    elif "<Vehicle Destruction>" in line:
                        timestamp = self.parse_timestamp(line)
                        match = re.search(
                            r"Vehicle '(?P<vehicle>[^']+)'.*?destroy level (?P<from_level>\d) to (?P<to_level>\d).*?caused by '(?P<causer>[^']+)' \[\d+\] with '(?P<dmg>[^']+)'",
                            line
                        )
                        if match:
                            raw_vehicle = match.group("vehicle")
                            vehicle_name = self.extract_clean_vehicle_name(raw_vehicle)
                            from_level = int(match.group("from_level"))
                            to_level = int(match.group("to_level"))
                            causer_raw = match.group("causer")
                            dmg_type = match.group("dmg")

                            causer_clean = self.extract_clean_vehicle_name(causer_raw)

                            # Determine kill type text
                            if dmg_type == "Collision":
                                output_line = f"{timestamp} - {vehicle_name} collided with {causer_clean}\n"
                            else:
                                if from_level == 0 and to_level == 1:
                                    kill_type = f"Soft Kill ({vehicle_name})"
                                elif (from_level == 1 and to_level == 2) or (from_level == 0 and to_level == 2):
                                    kill_type = f"Hard Kill ({vehicle_name})"
                                else:
                                    kill_type = f"Unknown Kill Type ({from_level}->{to_level}) ({vehicle_name})"
                                output_line = f"{timestamp} - {causer_raw} >> {kill_type}\n"

                            # Decide tag
                            if causer_raw == self.player_name:
                                tag = "player_kill"
                            else:
                                tag = "other_kill"

                            # Show if meets filter
                            if (
                                (tag == "player_kill" and self.show_player_kills.get()) or
                                (tag == "player_death" and self.show_other_kills.get()) or
                                (tag == "other_kill" and self.show_misc_kills.get())
                            ):
                                self.text_widget.insert(tk.END, output_line, tag)



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
