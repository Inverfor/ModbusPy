import tkinter as tk
from tkinter import ttk, messagebox

class UserInputGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("User Input GUI")
        self.root.geometry("500x400")
        
        self.create_widgets()
    
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Name input
        ttk.Label(main_frame, text="Name:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(main_frame, textvariable=self.name_var, width=30)
        self.name_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # Age input
        ttk.Label(main_frame, text="Age:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.age_var = tk.StringVar()
        self.age_entry = ttk.Entry(main_frame, textvariable=self.age_var, width=30)
        self.age_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # Email input
        ttk.Label(main_frame, text="Email:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.email_var = tk.StringVar()
        self.email_entry = ttk.Entry(main_frame, textvariable=self.email_var, width=30)
        self.email_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # Gender selection
        ttk.Label(main_frame, text="Gender:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.gender_var = tk.StringVar()
        gender_frame = ttk.Frame(main_frame)
        gender_frame.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Radiobutton(gender_frame, text="Male", variable=self.gender_var, value="Male").pack(side=tk.LEFT)
        ttk.Radiobutton(gender_frame, text="Female", variable=self.gender_var, value="Female").pack(side=tk.LEFT)
        ttk.Radiobutton(gender_frame, text="Other", variable=self.gender_var, value="Other").pack(side=tk.LEFT)
        
        # Country dropdown
        ttk.Label(main_frame, text="Country:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.country_var = tk.StringVar()
        countries = ["Select Country", "United States", "Canada", "United Kingdom", "Australia", "Germany", "France", "Japan", "Other"]
        self.country_combo = ttk.Combobox(main_frame, textvariable=self.country_var, values=countries, state="readonly")
        self.country_combo.grid(row=4, column=1, sticky=(tk.W, tk.E), pady=5)
        self.country_combo.current(0)
        
        # Interests checkboxes
        ttk.Label(main_frame, text="Interests:").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.interests_frame = ttk.Frame(main_frame)
        self.interests_frame.grid(row=5, column=1, sticky=(tk.W, tk.E), pady=5)
        
        self.sports_var = tk.BooleanVar()
        self.music_var = tk.BooleanVar()
        self.reading_var = tk.BooleanVar()
        self.travel_var = tk.BooleanVar()
        
        ttk.Checkbutton(self.interests_frame, text="Sports", variable=self.sports_var).grid(row=0, column=0, sticky=tk.W)
        ttk.Checkbutton(self.interests_frame, text="Music", variable=self.music_var).grid(row=0, column=1, sticky=tk.W)
        ttk.Checkbutton(self.interests_frame, text="Reading", variable=self.reading_var).grid(row=1, column=0, sticky=tk.W)
        ttk.Checkbutton(self.interests_frame, text="Travel", variable=self.travel_var).grid(row=1, column=1, sticky=tk.W)
        
        # Comments text area
        ttk.Label(main_frame, text="Comments:").grid(row=6, column=0, sticky=(tk.W, tk.N), pady=5)
        self.comments_text = tk.Text(main_frame, height=4, width=30, wrap=tk.WORD)
        self.comments_text.grid(row=6, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # Scrollbar for comments
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.comments_text.yview)
        scrollbar.grid(row=6, column=2, sticky=(tk.N, tk.S), pady=5)
        self.comments_text.configure(yscrollcommand=scrollbar.set)
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=7, column=0, columnspan=3, pady=20)
        
        # Submit button
        self.submit_btn = ttk.Button(buttons_frame, text="Submit", command=self.submit_form)
        self.submit_btn.pack(side=tk.LEFT, padx=5)
        
        # Clear button
        self.clear_btn = ttk.Button(buttons_frame, text="Clear", command=self.clear_form)
        self.clear_btn.pack(side=tk.LEFT, padx=5)
        
        # Display results area
        ttk.Label(main_frame, text="Results:").grid(row=8, column=0, sticky=(tk.W, tk.N), pady=5)
        self.results_text = tk.Text(main_frame, height=6, width=30, wrap=tk.WORD, state=tk.DISABLED)
        self.results_text.grid(row=8, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # Scrollbar for results
        results_scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.results_text.yview)
        results_scrollbar.grid(row=8, column=2, sticky=(tk.N, tk.S), pady=5)
        self.results_text.configure(yscrollcommand=results_scrollbar.set)
    
    def submit_form(self):
        # Collect all input data
        name = self.name_var.get().strip()
        age = self.age_var.get().strip()
        email = self.email_var.get().strip()
        gender = self.gender_var.get()
        country = self.country_var.get()
        comments = self.comments_text.get("1.0", tk.END).strip()
        
        # Collect interests
        interests = []
        if self.sports_var.get():
            interests.append("Sports")
        if self.music_var.get():
            interests.append("Music")
        if self.reading_var.get():
            interests.append("Reading")
        if self.travel_var.get():
            interests.append("Travel")
        
        # Basic validation
        if not name:
            messagebox.showerror("Error", "Please enter your name!")
            return
        
        if not age:
            messagebox.showerror("Error", "Please enter your age!")
            return
        
        try:
            age_int = int(age)
            if age_int < 0 or age_int > 150:
                messagebox.showerror("Error", "Please enter a valid age (0-150)!")
                return
        except ValueError:
            messagebox.showerror("Error", "Age must be a number!")
            return
        
        if not email or "@" not in email:
            messagebox.showerror("Error", "Please enter a valid email address!")
            return
        
        if not gender:
            messagebox.showerror("Error", "Please select your gender!")
            return
        
        if country == "Select Country":
            messagebox.showerror("Error", "Please select your country!")
            return
        
        # Display results
        result_text = f"Form Submitted Successfully!\n\n"
        result_text += f"Name: {name}\n"
        result_text += f"Age: {age}\n"
        result_text += f"Email: {email}\n"
        result_text += f"Gender: {gender}\n"
        result_text += f"Country: {country}\n"
        result_text += f"Interests: {', '.join(interests) if interests else 'None'}\n"
        if comments:
            result_text += f"Comments: {comments}\n"
        
        self.results_text.config(state=tk.NORMAL)
        self.results_text.delete("1.0", tk.END)
        self.results_text.insert("1.0", result_text)
        self.results_text.config(state=tk.DISABLED)
        
        messagebox.showinfo("Success", "Form submitted successfully!")
    
    def clear_form(self):
        # Clear all input fields
        self.name_var.set("")
        self.age_var.set("")
        self.email_var.set("")
        self.gender_var.set("")
        self.country_combo.current(0)
        self.sports_var.set(False)
        self.music_var.set(False)
        self.reading_var.set(False)
        self.travel_var.set(False)
        self.comments_text.delete("1.0", tk.END)
        
        # Clear results
        self.results_text.config(state=tk.NORMAL)
        self.results_text.delete("1.0", tk.END)
        self.results_text.config(state=tk.DISABLED)

def main():
    root = tk.Tk()
    app = UserInputGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()