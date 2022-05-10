import tkinter as tk
from tkinter import ttk
from tkinter.filedialog import askopenfilename, asksaveasfilename
from tkinter import messagebox

import os, json, pyperclip

from pystray import MenuItem as item
import pystray
from PIL import Image, ImageTk

from VerticalScrollFrame import ScrollFrame
from collections import namedtuple

Tab = namedtuple("Tab", ["children", "widget"])
Button = namedtuple("Button", ["description", "codestring", "widget"])

class EntryPopup():
    
    def __init__(self, window):
        self.popupWindow = tk.Toplevel(window)
        
        # Frame for main body
        self.input_container = ttk.Frame(self.popupWindow)
        self.input_container.pack(side='top', fill='both', expand=True, padx=10, pady=5)

        # Frame for buttons at bottom
        self.button_container = ttk.Frame(self.popupWindow)
        self.button_container.pack(side='top', fill='x', padx=20, pady=5)            
        
    def add_entry(self, label):
        label_widget = ttk.Label(self.input_container, text=label)
        label_widget.pack(side='top', fill='x', expand=False)
        
        entry_contents = tk.StringVar(self.popupWindow)
        text_entry = ttk.Entry(self.input_container, textvariable=entry_contents)
        text_entry.pack(side='top', fill='both', expand=False)
        
        return entry_contents
    
    def add_text(self, label):
        label_widget = ttk.Label(self.input_container, text=label)
        label_widget.pack(side='top', fill='x', expand=False) 
        
        text_entry_frame = ttk.Frame(self.input_container)
        text_entry_frame.pack(side='top', fill='both', expand=True)  
        
        text_entry = tk.Text(text_entry_frame, height=1, width=1)
        text_entry.pack(side='left', fill='both', expand=True)   
        
        scrollbar = ttk.Scrollbar(text_entry_frame, orient='vertical', command=text_entry.yview)
        scrollbar.pack(side='right', fill='y')
        text_entry['yscrollcommand'] = scrollbar.set 
        
        return text_entry
    
    def add_buttons(self, button_info):
        
        for name, command in button_info.items():
            submit_button = ttk.Button(self.button_container, text=name, command=command)
            submit_button.pack(side='left', expand=True)
        
        
    def size_popup(self):
        self.popupWindow.update()
        width, height = self.popupWindow.winfo_width(), self.popupWindow.winfo_height()
        self.popupWindow.minsize(300, height)
        
        
    def destroy(self):
        self.popupWindow.destroy()

        
class CheatSheet:

    def __init__(self, window):
        self._id_count = 0
        self.edit_mode = False
        
        # Set the size of the window
        window.geometry("350x350-50-50")
        window.resizable(False, True)        

        self.fp = "cheatsheet.json"

        self.window = window
        window.title("CheatSheet")
        
        self.tabs = {}
        self.buttons = {}
        self.generate_gui()

        buttonRow = ttk.Frame(window)
        buttonRow.pack(expand=False, fill="x", side="bottom")

        addItemButton = ttk.Button(buttonRow,
                                   text='Add Item',
                                   command=self.add_item_popup)
        addItemButton.pack(expand=True, fill='y', side="left", padx=5, pady=5)

        editItemButton = ttk.Button(buttonRow,
                                    text='Edit Items',
                                    command=self.edit_items)
        editItemButton.pack(expand=True, fill='y', side="left", padx=5, pady=5)   

        addTabButton = ttk.Button(buttonRow,
                                  text='Add Tab',
                                  command=self.create_tab_popup)
        addTabButton.pack(expand=True, fill='y', side="left", padx=5, pady=5)   

        deleteTabButton = ttk.Button(buttonRow,
                                     text='Delete Tab',
                                     command=self.delete_tab_popup)
        deleteTabButton.pack(expand=True, fill='y', side="left", padx=5, pady=5)   
            
    
    def load_cheatsheet(self):
        """Retrieve cheatsheet info from json file."""
        if not os.path.isfile(self.fp):
            with open(self.fp, "w", encoding="utf-8") as cheatsheet:
                json.dump({"Tab 1": []}, cheatsheet)

        with open(self.fp, encoding="utf-8") as cheatsheet:
            cs_dict = json.load(cheatsheet)
            if not cs_dict:
                cs_dict = {"Tab 1": []}
        
        return cs_dict
    
    def save_cheatsheet(self):
        cs_dict = {}
        for tab_name, tab_info in self.tabs.items():
            children = []
            for button_id in tab_info.children:
                button_info = self.buttons[button_id]
                children.append([button_info.description,
                                 button_info.codestring])
                
            cs_dict[tab_name] = children
        
        with open(self.fp, 'w', encoding='utf-8') as cheatsheet:
            json.dump(cs_dict, cheatsheet, indent=4)
    
    def save(f):
        def inner(self, *args, **kwargs):
            f(self, *args, **kwargs)
            
            self.save_cheatsheet()
                
        return inner
    
    def reload_gui(f):
        def inner(self, *args, **kwargs):
            f(self, *args, **kwargs)
            
            for tab_info in self.tabs.values():
                for button_id in tab_info.children:
                    button = self.buttons[button_id].widget
                    button.pack(fill='x', side='top', padx=10, pady=5)   
                
        return inner

    def clear_tab(f):
        def inner(self, tab_name, *args, **kwargs):
            self.tabs[tab_name] = tab_frame
            
            for child in tab_frame.winfo_children():
                child.unpack()
                
            f(self, tab_name, *args, **kwargs)
        return inner

    @reload_gui
    def generate_gui(self):
        cs_dict = self.load_cheatsheet()
        
        tabControl = ttk.Notebook(window)
        tabControl.bind('<Double-Button-1>', self.edit_tab_popup)
        tabControl.pack(expand=1, fill="both")   
        
        self.tabControl = tabControl

        for tab_name, children in cs_dict.items():
            self.generate_tab(tab_name, children)

    def generate_tab(self, tab_name, current_children=None):
        if current_children is None:
            current_children = []
        
        tab_frame = ScrollFrame(self.tabControl)
        
        children = []
        self.tabs[tab_name] = Tab(children, tab_frame)
        self.tabControl.add(tab_frame, text=tab_name)
   
        for button_info in current_children:
            button_id = self.generate_button(*button_info, tab_frame)
            children.append(button_id)
                 
    def generate_button(self, description, code_string, tab_frame):
        
        button_id = self._id_count
        self._id_count += 1
        
        s = ttk.Style()
        s.configure('LeftAlign.TButton', anchor='w')        
        
        button = ttk.Button(tab_frame.viewPort,
                            style='LeftAlign.TButton',
                            command=lambda: self.button_command(button_id))#pyperclip.copy(code_string))

        description_var = tk.StringVar(button, value=description, name=f'{button_id} description')
        codestring_var = tk.StringVar(button, value=code_string, name=f'{button_id} codestring')

        button.config(textvariable=description_var)

        self.buttons[button_id] = Button(description_var, codestring_var, button)
            
        return button_id
            
    
    def button_command(self, button_id):
        if self.edit_mode:
            self.edit_button_popup(button_id)
        else:
            pyperclip.copy(self.buttons[button_id].codestring.get())


    def add_item_popup(self):
        addItemPopup = EntryPopup(self.window)
        desc_var = addItemPopup.add_entry("Description")
        code_string_widget = addItemPopup.add_text("Code String")
        
        # submit button
        def submit_action():
            tab_name = self.tabControl.tab(self.tabControl.select(), "text")
            self.add_item(desc_var.get(), code_string_widget.get("1.0",'end-1c'), tab_name)
            addItemPopup.destroy()        
        
        addItemPopup.add_buttons({"Submit": submit_action,
                                  "Cancel": addItemPopup.destroy})    
        
        addItemPopup.size_popup()

    @save
    @reload_gui
    def add_item(self, desc, code_string, tab_name):
        """Add item to json dict and save it."""
        
        button_id = self.generate_button(desc, code_string, self.tabs[tab_name].widget)
        self.tabs[tab_name].children.append(button_id)
        
        
    def edit_items(self):
        # Do something to show its in edit mode
        self.edit_mode = not self.edit_mode

    def edit_button_popup(self, button_id):
        editItemPopup = EntryPopup(self.window)
        desc_var = editItemPopup.add_entry("New Description")
        code_string_widget = editItemPopup.add_text("New Code String")

        # submit button
        def submit_action():
            tab_name = self.tabControl.tab(self.tabControl.select(), "text")
            self.edit_button(desc_var.get(),
                             code_string_widget.get("1.0",'end-1c'))
            editItemPopup.destroy()

        def delete_action(button_id):
            current_tab = self.tabControl.tab(self.tabControl.select(), "text")
            confirmation = messagebox.askyesno(title="Delete Tab", message=f"Are you sure you want to delete button '{current_tab}'?")
            if confirmation:
                editItemPopup.destroy()


        editItemPopup.add_buttons({"Submit": submit_action,
                                    "Delete": lambda: delete_action(button_id),
                                    "Cancel": editItemPopup.destroy})
        editItemPopup.size_popup()

    def edit_button(self, *new_info):
        pass


    def create_tab_popup(self):
        createTabPopup = EntryPopup(self.window)
        tab_name_var = createTabPopup.add_entry("New Tab Name")
        
        # submit button
        def submit_action():
            self.create_tab(tab_name_var.get())
            createTabPopup.destroy()        
        
        createTabPopup.add_buttons({"Submit": submit_action,
                                    "Cancel": createTabPopup.destroy})
        createTabPopup.size_popup()

    @save
    def create_tab(self, tab_name):
        """Add a tab to the json dict and save it."""            
        self.generate_tab(tab_name)
            
    
    def delete_tab_popup(self):
        current_tab = self.tabControl.tab(self.tabControl.select(), "text")  
        confirmation = messagebox.askyesno(title="Delete Tab", message=f"Are you sure you want to delete tab '{current_tab}'?\n\nAll buttons within will be lost.")
        if confirmation:
            self.delete_tab(current_tab)
    
    @save
    def delete_tab(self, tab_name):
        self.tabs[tab_name].destroy()
        del self.tabs[tab_name]
        
        
    def edit_tab_popup(self, event):
        current_tab = self.tabControl.tab(self.tabControl.select(), "text")  
        
        editTabPopup = EntryPopup(self.window)
        tab_name_var = editTabPopup.add_entry(f"Change '{current_tab}' to:")
        
        # submit button
        def submit_action():
            self.edit_tab(current_tab, tab_name_var.get())
            editTabPopup.destroy()   
        
        editTabPopup.add_buttons({"Submit": submit_action,
                                  "Cancel": editTabPopup.destroy})  
        editTabPopup.size_popup()

    @save        
    def edit_tab(self, current_tab, new_tab_name):
        self.tabs[new_tab_name] = self.tabs[current_tab]
        del self.tabs[current_tab]
        
        tab_frame = self.tabs[new_tab_name].widget
        self.tabControl.tab(tab_frame, text=new_tab_name)



if __name__ == '__main__':
    window = tk.Tk()

    app = CheatSheet(window)

    # Define a function for quit the window
    def quit_window(icon, item):
        icon.stop()
        window.destroy()

    # Define a function to show the window again
    def show_window(icon, item):
        icon.stop()
        window.after(0, window.deiconify())
    
    # Hide the window and show on the system taskbar
    def hide_window():
        #app.save_cheatsheet()
        window.withdraw()
        image=Image.open("favicon.ico")
        menu=(item('Show', show_window), item('Quit', quit_window))
        icon=pystray.Icon("name", image, "My System Tray Icon", menu)
        icon.run()
        
    window.protocol('WM_DELETE_WINDOW', hide_window)
    window.attributes("-topmost", True)
        
    window.mainloop()
