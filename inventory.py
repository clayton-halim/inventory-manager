from operator import itemgetter
import random
import re

import numpy as np
import tkinter as tk
import tkinter.font as tkFont
import tkinter.ttk as ttk

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
        self.filtered_items_ix = range(len(items))  # indexes of filtered items

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

        for ix in self.filtered_items_ix:
            self.tree.insert('', index='end', values=self.items[ix])

            # Ensure column width fits values
            for i in range(len(self.header)):
                col_width = tkFont.Font().measure(self.items[ix][i]) + 20
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
        for ix in self.filtered_items_ix:
            self.tree.insert('', index='end', values=self.items[ix])

class AssetList(MultiColumnListbox):
    def __init__(self, master, app_toplevel, header, items):
        MultiColumnListbox.__init__(self, master, header, items)
        self.master = master
        self.app_toplevel = app_toplevel

        # Asset list tree configurations
        self.tree.configure(selectmode=tk.BROWSE)  # One item selection at a time
        self.tree.bind('<Double-Button-1>', self.select_item)
        self.tree.bind('<Return>', self.select_item)
        self.tree.tag_configure('Borrowed', background='#F44336')
        self.tree.tag_configure('Shopping Cart', background='#80DEEA')
        self.items.sort(key=itemgetter(COLUMN_INDEX['Asset Number']))
        self.repopulate_list()

    def repopulate_list(self):
        """
        Refreshes the view of the list
        """

        for row in self.tree.get_children():
                self.tree.delete(row)
        for ix in self.filtered_items_ix:
            item = self.items[ix]
            self.tree.insert('', index='end', values=item, 
                                tags=[item[COLUMN_INDEX['State']]])

    def select_item(self, *args):
        item = self.tree.item(self.tree.focus())
        item_index = self.tree.index(self.tree.focus())
        full_list_index = self.filtered_items_ix[item_index]

        if item['values'] != '':
            asset_number = item['values'][COLUMN_INDEX['Asset Number']]
            item_name = item['values'][COLUMN_INDEX['Item']]
            item_state = item['values'][COLUMN_INDEX['State']]
            new_values = item['values']
            
            if item_state == 'Available':
                self.app_toplevel.history_msg.set('{} was put into shopping cart'.format(item_name))
                new_values[COLUMN_INDEX['State']] = 'Shopping Cart'

                # Edit the item in the initial non-filtered list
                self.app_toplevel.shopping_cart.filtered_items_ix.append(full_list_index)
                self.app_toplevel.update_cart_count()
                self.app_toplevel.shopping_cart.tree.insert('', 'end', values=new_values)

            elif item_state == 'Shopping Cart':
                # Remove item from shopping cart
                self.app_toplevel.history_msg.set('{} was removed from shopping cart'.format(item_name))
                new_values[COLUMN_INDEX['State']] = 'Available'

                for filter_index, ix in enumerate(self.app_toplevel.shopping_cart.filtered_items_ix):
                    current = self.app_toplevel.shopping_cart.items[ix]
                    if current[COLUMN_INDEX['Asset Number']] == asset_number:
                        del self.app_toplevel.shopping_cart.filtered_items_ix[filter_index]
                        self.app_toplevel.update_cart_count()
                        break

                # Remove listing in shopping cart gui
                for leaf_id in self.app_toplevel.shopping_cart.tree.get_children(''):
                    current = self.app_toplevel.shopping_cart.tree.item(leaf_id)

                    if asset_number == current['values'][COLUMN_INDEX['Asset Number']]:
                        self.app_toplevel.shopping_cart.tree.delete(leaf_id)
                        break

            self.items[full_list_index] = new_values
            self.tree.item(self.tree.focus(), values=new_values, tags=[new_values[COLUMN_INDEX['State']]])

class ShoppingCart(MultiColumnListbox):
    def __init__(self, master, app_toplevel, header, items):
        MultiColumnListbox.__init__(self, master, header, items)
        self.master = master
        self.app_toplevel = app_toplevel
        self.tree.bind('<Double-Button-1>', self.select_item)
        self.filtered_items_ix = []
        self.repopulate_list()

    def select_item(self, *args):
        item = self.tree.item(self.tree.focus())

        if item['values'] != '':
            item_index = self.tree.index(self.tree.focus())
            full_list_index = self.filtered_items_ix[item_index]
            asset_number = item['values'][COLUMN_INDEX['Asset Number']]
            item_name = item['values'][COLUMN_INDEX['Item']]
            item_state = item['values'][COLUMN_INDEX['State']]
            new_values = item['values']

            self.app_toplevel.history_msg.set('{} was removed from shopping cart'.format(item_name))
            new_values[COLUMN_INDEX['State']] = 'Available'

            # Remove from shopping cart
            for filter_index, ix in enumerate(self.app_toplevel.shopping_cart.filtered_items_ix):
                current = self.app_toplevel.shopping_cart.items[ix]
                if current[COLUMN_INDEX['Asset Number']] == asset_number:
                    del self.filtered_items_ix[filter_index]
                    self.app_toplevel.update_cart_count()
                    break

            self.items[full_list_index] = new_values
            self.tree.delete(self.tree.focus())

            # Update item listing in asset list
            for leaf_id in self.app_toplevel.asset_list.tree.get_children(''):
                current = self.app_toplevel.asset_list.tree.item(leaf_id)

                if asset_number == current['values'][COLUMN_INDEX['Asset Number']]:
                    self.app_toplevel.asset_list.tree.item(leaf_id, 
                        values=new_values, tags=[new_values[COLUMN_INDEX['State']]])
                    break


class Application(object):
    def __init__(self, master):
        self.master = master
        self.master.rowconfigure(0, weight=1)
        self.master.columnconfigure(0, weight=1)

        # Items
        self.asset_list_header = [header[0] for header in 
                                    sorted([(column, COLUMN_INDEX[column]) 
                                                for column in COLUMN_INDEX], key=lambda c: c[1])]
        self.asset_list_items = [[0, 
                                  items[random.randint(0, len(items) - 1)], 
                                  states[random.randint(0, len(states) - 2)],
                                  'John Smith',
                                  'John.Smith@drdc-rddc.gc.ca',
                                  'Jul 28'] 
                                    for i in range(100)]
        for i, id_ in enumerate(np.random.choice(100, 100, replace=False)):
            self.asset_list_items[i][0] = id_

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

        # Item Description Frame
        self.item_frame = ttk.LabelFrame(self.asset_frame, text='Description')
        self.item_frame.rowconfigure(0, weight=1)
        self.item_frame.columnconfigure(0, weight=1)
        self.item_frame.grid(row=2, column=0, sticky='nesw', padx=10, pady=10)

        self.item_msg = tk.Text(self.item_frame, wrap=tk.WORD, state=tk.DISABLED, height=3)
        self.item_msg.grid(row=0, column=0, sticky='nesw')
        msg_vsb = ttk.Scrollbar(self.item_frame, orient=tk.VERTICAL, command=self.item_msg.yview)
        msg_vsb.grid(row=0, column=1, sticky='nes')

        self.item_msg.configure(state=tk.NORMAL)
        self.item_msg.insert(tk.END, 'This item is very new. No scratches, 100% great! If you have any questions please ask.')
        self.item_msg.configure(state=tk.DISABLED)

        # History message
        self.history_msg = tk.StringVar()
        self.history_msg.set('No action performed yet')
        self.history_label = tk.Label(self.asset_frame, textvariable=self.history_msg, justify=tk.LEFT,
                                        anchor=tk.W)
        self.history_label.grid(row=3, column=0, sticky='nesw')

        # Shopping cart frame
        self.cart_frame = tk.Frame(self.notebook, name='cart_frame')
        self.cart_frame.grid(row=0, column=0, sticky='nesw')
        self.cart_frame.rowconfigure(0, weight=1)
        self.cart_frame.columnconfigure(0, weight=1)
        self.notebook.add(self.cart_frame, text='Shopping Cart (0)') 

        # Shopping cart list
        self.shopping_cart_header = ['Asset Number', 'Item']
        self.shopping_cart = ShoppingCart(self.cart_frame, self, self.shopping_cart_header, self.asset_list_items)
        self.shopping_cart.grid(row=0, column=0, sticky='nesw')
        self.shopping_cart.rowconfigure(0, weight=1)
        self.shopping_cart.columnconfigure(0, weight=1)

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
            self.asset_list.filtered_items_ix = [index for index in range(len(self.asset_list.items))
                                                    if self._match_searchables(query, self.asset_list.items[index])]
        else:
            self.asset_list.filtered_items_ix = range(len(self.asset_list.items))

        self.asset_list.repopulate_list()

    def update_cart_count(self):
        self.notebook.tab('.!notebook.cart_frame', 
                    text='Shopping Cart ({})'.format(len(self.shopping_cart.filtered_items_ix)))

def main():
    root = tk.Tk()
    app = Application(root)
    root.title('Inventory Manager')
    root.update()
    root.mainloop()

if __name__ == '__main__':
    main()
