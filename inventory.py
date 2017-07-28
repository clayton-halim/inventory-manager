import tkinter as tk
import tkinter.font as tkFont
import tkinter.ttk as ttk

import random
import numpy as np
import re

COLUMN_INDEX = {'Asset Number': 0, 'Item': 1, 'State': 2, 'Loaned To': 3, 'Email': 4, 'Due Date': 5}
SEARCHABLE = ['Asset Number', 'Item', 'Loaned To', 'Email', 'Due Date']
SEARCH_HINT = 'search...'

# TEMPORARY DUMMY DATA
items = ['Laptop', 'Microphone', 'Pen', 'Monitor', 'Keyboard', 'Strapped Bag',
            'Mouse', 'Notebook', 'CD', 'USB Stick', 'Desk', 'Key']
states = ['Available', 'Borrowed', 'Shopping Cart']

class MultiColumnListbox(tk.Frame):
    def __init__(self, master, header, items):
        tk.Frame.__init__(self, master)
       
        self.header = header
        self.items = items

        self.tree = ttk.Treeview(self, columns=self.header, show='headings')
        v_scroll = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        h_scroll = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        self.tree.grid(row=0, column=0, sticky='nesw')
        v_scroll.grid(row=0, column=1, sticky='ns')
        h_scroll.grid(row=1, column=0, sticky='ew')

        self._build_tree()

    def _build_tree(self):
        """
        Initializes the items in the tree to be displayed on the gui
        """

        for col in self.header:
            self.tree.heading(col, text=col.title(),
                                command=lambda c=col: self.sortby(c, True))
            self.tree.column(col, width=tkFont.Font().measure(col.title())+20)  # +20 for extra padding

        for item in self.items:
            self.tree.insert('', index='end', values=item)

        # Ensure column width fits values
        for i, val in enumerate(item):
            col_width = tkFont.Font().measure(val) + 20
            if self.tree.column(self.header[i], width=None) < col_width:
                self.tree.column(self.header[i], width=col_width)

    def sortby(self, col, descending):
        """
        Sorts the data in a list column
        """

        data = [(self.tree.set(child, col), child) for child in self.tree.get_children('')]
        data.sort(reverse=descending)

        for i, item in enumerate(data):
            self.tree.move(item[1], '', i)

        self.tree.heading(col, command=lambda c=col: self.sortby(c, not descending))

    def repopulate_list(self):
        """
        Refreshes the view of the list
        """

        for row in self.tree.get_children():
                self.tree.delete(row)
        for item in self.items:
            self.tree.insert('', index='end', values=item)

class AssetList(MultiColumnListbox):
    def __init__(self, master, app_toplevel, header, items):
        MultiColumnListbox.__init__(self, master, header, items)
        self.master = master
        self.app_toplevel = app_toplevel

        # Asset list tree configurations
        self.tree.configure(selectmode=tk.BROWSE)
        self.tree.bind('<Double-Button-1>', self.select_item)
        self.tree.bind('<Return>', self.select_item)
        self.tree.tag_configure('Borrowed', background='#F44336')
        self.tree.tag_configure('Shopping Cart', background='#80DEEA')

        self.items_filtered = range(len(self.items))

    def repopulate_list(self):
        """
        Refreshes the view of the list
        """

        for row in self.tree.get_children():
                self.tree.delete(row)
        for index in self.items_filtered:
            self.tree.insert('', index='end', values=self.items[index])

    def select_item(self, *args):
        pass

class Application(object):
    def __init__(self, master):
        self.master = master
        self.master.rowconfigure(0, weight=1)
        self.master.columnconfigure(0, weight=1)

        # Items
        self.asset_list_header = [header[0] for header in 
                                    sorted([(column, COLUMN_INDEX[column]) 
                                                for column in COLUMN_INDEX], key=lambda c: c[1])]
        self.asset_list_items = [(random.randint(1, 1000), 
                                  items[random.randint(0, len(items) - 1)], 
                                  states[random.randint(0, len(states) - 2)],
                                  'John Smith',
                                  'John.Smith@drdc-rddc.gc.ca',
                                  'Jul 28') 
                                    for i in range(100)]

        # Tabs for asset list / shopping cart
        self.notebook = ttk.Notebook(self.master)
        self.notebook.grid(row=0, column=0, sticky='nesw')
        self.notebook.rowconfigure(0, weight=1)
        self.notebook.columnconfigure(0, weight=1)

        # Asset list frame
        self.asset_frame = ttk.Frame(self.notebook, name='asset_frame')
        self.asset_frame.grid(row=0, column=0, sticky='nesw')
        self.asset_frame.rowconfigure(1, weight=1)
        self.asset_frame.columnconfigure(0, weight=1)
        self.notebook.add(self.asset_frame, text='Asset List')

        # Search bar
        self.search_query = tk.StringVar()
        self.search_query.set('search...')
        self.search_bar = tk.Entry(self.asset_frame, exportselection=0, textvariable=self.search_query)
        self.search_bar.grid(row=0, column=0,
                                 sticky=tk.N+tk.W+tk.E)
        self.search_bar.bind('<FocusIn>', self.search_clear)
        self.search_query.trace('w', self.search)

        # Asset List
        self.asset_list = AssetList(self.asset_frame, self, self.asset_list_header, self.asset_list_items)
        self.asset_list.grid(row=1, column=0, sticky='nesw')
        self.asset_list.rowconfigure(0, weight=1)
        self.asset_list.columnconfigure(0, weight=1)
        
    def _match_searchables(self, query, columns):
        """
        Goes through all searchable columns and returns True if query matches at least one, else False
        """

        for column in SEARCHABLE:
            if re.search(query, str(columns[COLUMN_INDEX[column]]), re.IGNORECASE):
                return True 
        return False
        
    def search_clear(self, *args):
        """
        Clears the search bar if the search hint is present
        """

        if self.search_bar.get() == SEARCH_HINT:
            self.search_query.set('')

    def search(self, *args):
        """
        Filters the indexes of the asset list that matches the search query, then refreshes the list view
        """
        
        query = self.search_bar.get() 
        if len(query) > 0 and query != SEARCH_HINT:
            self.asset_list.items_filtered = [index for index in range(len(self.asset_list.items))
                                                if self._match_searchables(query, self.asset_list.items[index])]
        else:
            self.asset_list.items_filtered = range(len(self.asset_list.items_filtered))

        self.asset_list.repopulate_list()

def main():
    root = tk.Tk()
    app = Application(root)
    root.title('Inventory Manager')
    root.update()
    root.mainloop()

if __name__ == '__main__':
    main()
