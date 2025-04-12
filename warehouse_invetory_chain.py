import hashlib
import datetime
import json
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import pickle
import os

# --- Blockchain Components ---

class Block:
    """Represents a single block in the blockchain."""
    def __init__(self, index, timestamp, transactions, previous_hash, nonce=0):
        self.index = index
        self.timestamp = timestamp
        self.transactions = transactions  # List of transactions in this block
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.calculate_hash() # Calculate hash upon creation

    def calculate_hash(self):
        """Calculates the SHA-256 hash of the block's contents."""
        # Ensure transactions are consistently ordered for hashing if they are dicts
        # For simple strings/numbers, direct json dumps is okay.
        block_string = json.dumps({
            "index": self.index,
            "timestamp": str(self.timestamp), # Convert datetime to string
            "transactions": self.transactions,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }, sort_keys=True).encode() # sort_keys ensures consistent hash
        return hashlib.sha256(block_string).hexdigest()

    def mine_block(self, difficulty):
        """
        Finds a nonce such that the block's hash starts with a certain number of zeros.
        Simple Proof-of-Work.
        """
        target = '0' * difficulty
        while not self.hash.startswith(target):
            self.nonce += 1
            self.hash = self.calculate_hash()
        # print(f"Block mined: {self.hash}") # Optional: for debugging

class Blockchain:
    """Manages the chain of blocks."""
    def __init__(self, difficulty=2, chain_file="blockchain_data.pkl"):
        self.chain_file = chain_file
        self.chain = []
        self.pending_transactions = []
        self.difficulty = difficulty # PoW difficulty

        # Load existing chain or create genesis block
        if os.path.exists(self.chain_file):
            self.load_chain()
        else:
             self.create_genesis_block()
             self.save_chain() # Save initial chain

    def create_genesis_block(self):
        """Creates the first block in the chain."""
        genesis_block = Block(0, datetime.datetime.now(), "Genesis Block", "0")
        # No mining needed for genesis usually, but we can mine it too
        genesis_block.mine_block(self.difficulty)
        self.chain.append(genesis_block)

    def get_latest_block(self):
        """Returns the most recent block in the chain."""
        return self.chain[-1]

    def add_transaction(self, transaction):
        """
        Adds a new transaction to the list of pending transactions.
        Transaction format: {'item_id': 'SKU123', 'change': 10} or {'item_id': 'SKU456', 'change': -5}
        """
        if not isinstance(transaction, dict) or 'item_id' not in transaction or 'change' not in transaction:
            print("Error: Invalid transaction format.")
            return False

        # Basic validation (optional but good)
        try:
            int(transaction['change']) # Check if change is numeric
            str(transaction['item_id']) # Check if item_id is string-like
        except ValueError:
            print("Error: Transaction 'change' must be a number.")
            return False
        except TypeError:
             print("Error: Transaction 'item_id' or 'change' has wrong type.")
             return False

        self.pending_transactions.append(transaction)
        print(f"Transaction added: {transaction}") # Debug
        return True

    def mine_pending_transactions(self):
        """
        Mines a new block containing all pending transactions.
        """
        if not self.pending_transactions:
            print("No pending transactions to mine.")
            return False # Indicate nothing was mined

        print("Starting mining...") # Debug
        latest_block = self.get_latest_block()
        new_block = Block(
            index=latest_block.index + 1,
            timestamp=datetime.datetime.now(),
            transactions=self.pending_transactions, # Add all pending
            previous_hash=latest_block.hash
        )
        new_block.mine_block(self.difficulty)

        print(f"New block mined successfully. Hash: {new_block.hash}") # Debug
        self.chain.append(new_block)
        self.pending_transactions = [] # Clear pending transactions
        self.save_chain() # Persist the updated chain
        return True # Indicate mining happened

    def is_chain_valid(self):
        """Validates the integrity of the blockchain."""
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i-1]

            # Check if the block's stored hash is correct
            if current_block.hash != current_block.calculate_hash():
                print(f"Data Tampering Detected: Block {current_block.index} hash mismatch.")
                return False

            # Check if the block points to the correct previous block
            if current_block.previous_hash != previous_block.hash:
                print(f"Chain Broken: Block {current_block.index} previous hash mismatch.")
                return False

            # Check if the block's hash meets the difficulty requirement
            if not current_block.hash.startswith('0' * self.difficulty):
                 print(f"Proof of Work Invalid: Block {current_block.index} hash does not meet difficulty.")
                 return False

        return True

    def get_inventory(self):
        """Calculates the current inventory by processing all transactions."""
        if not self.is_chain_valid():
            messagebox.showerror("Error", "Blockchain is invalid! Inventory data may be corrupted.")
            return None # Indicate error

        inventory = {}
        # Start from block 1 (skip genesis block's string data)
        for block in self.chain[1:]:
            # Handle potential variations if transactions are sometimes single dicts
            block_transactions = block.transactions
            if isinstance(block_transactions, dict): # Handle case where a block might have only one transaction stored as a dict
                 block_transactions = [block_transactions]
            elif not isinstance(block_transactions, list):
                print(f"Warning: Skipping block {block.index} due to unexpected transaction format: {type(block_transactions)}")
                continue # Skip block if format is unknown

            for transaction in block_transactions:
                 # Defensive check within the loop
                 if isinstance(transaction, dict) and 'item_id' in transaction and 'change' in transaction:
                    item_id = transaction['item_id']
                    change = int(transaction['change']) # Ensure it's an int
                    inventory[item_id] = inventory.get(item_id, 0) + change
                 else:
                     print(f"Warning: Skipping invalid transaction in block {block.index}: {transaction}")


        # Filter out items with zero or negative stock if desired
        # inventory = {item: qty for item, qty in inventory.items() if qty > 0}
        return inventory

    def save_chain(self):
        """Saves the current blockchain state to a file using pickle."""
        try:
            with open(self.chain_file, 'wb') as f:
                pickle.dump(self.chain, f)
            # print("Blockchain saved.") # Debug
        except Exception as e:
            print(f"Error saving blockchain: {e}")
            messagebox.showerror("Save Error", f"Could not save blockchain data:\n{e}")

    def load_chain(self):
        """Loads the blockchain state from a file."""
        try:
            with open(self.chain_file, 'rb') as f:
                self.chain = pickle.load(f)
            print(f"Blockchain loaded from {self.chain_file}. Blocks: {len(self.chain)}") # Debug
            if not self.chain: # Handle empty file case
                 self.create_genesis_block()
                 self.save_chain()
            elif not self.is_chain_valid():
                 messagebox.showwarning("Load Warning", "Loaded blockchain failed validation. Check data integrity.")

        except FileNotFoundError:
            print("Blockchain file not found, creating new one.")
            self.create_genesis_block()
            self.save_chain()
        except Exception as e:
            print(f"Error loading blockchain: {e}")
            messagebox.showerror("Load Error", f"Could not load blockchain data:\n{e}\nStarting fresh.")
            # Fallback to a fresh chain if loading fails catastrophically
            self.chain = []
            self.pending_transactions = []
            self.create_genesis_block()
            self.save_chain()


# --- GUI Application ---

class InventoryApp:
    def __init__(self, root, blockchain):
        self.blockchain = blockchain
        self.root = root
        self.root.title("Blockchain Inventory Tracker")
        self.root.geometry("550x450") # Adjusted size

        # Styling
        style = ttk.Style()
        style.theme_use('alt') # Or 'clam', 'default', 'classic'

        # --- Input Frame ---
        input_frame = ttk.LabelFrame(root, text="Manage Stock")
        input_frame.pack(padx=10, pady=10, fill="x")

        ttk.Label(input_frame, text="Item ID:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.item_id_entry = ttk.Entry(input_frame, width=20)
        self.item_id_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(input_frame, text="Quantity:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.quantity_entry = ttk.Entry(input_frame, width=10)
        self.quantity_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        self.add_button = ttk.Button(input_frame, text="Add Stock", command=self.add_stock)
        self.add_button.grid(row=2, column=0, padx=5, pady=10)

        self.remove_button = ttk.Button(input_frame, text="Remove Stock", command=self.remove_stock)
        self.remove_button.grid(row=2, column=1, padx=5, pady=10, sticky="w")

        # --- Inventory Display Frame ---
        display_frame = ttk.LabelFrame(root, text="Current Inventory")
        display_frame.pack(padx=10, pady=5, fill="both", expand=True)

        self.inventory_display = scrolledtext.ScrolledText(display_frame, wrap=tk.WORD, width=60, height=15, state='disabled')
        self.inventory_display.pack(padx=5, pady=5, fill="both", expand=True)

        # --- Action/Status Frame ---
        action_frame = ttk.Frame(root)
        action_frame.pack(padx=10, pady=5, fill="x")

        self.refresh_button = ttk.Button(action_frame, text="Refresh Inventory", command=self.update_inventory_display)
        self.refresh_button.pack(side=tk.LEFT, padx=5)

        # Add mine button explicitly if not mining after every transaction
        # self.mine_button = ttk.Button(action_frame, text="Mine Pending", command=self.mine_and_refresh)
        # self.mine_button.pack(side=tk.LEFT, padx=5)

        self.status_label = ttk.Label(action_frame, text="Status: Ready", anchor="e")
        self.status_label.pack(side=tk.RIGHT, padx=5, fill="x", expand=True)

        # Load initial display
        self.update_inventory_display()

    def _add_transaction(self, item_id, quantity_change):
        """Internal helper to add transaction and mine."""
        if not item_id:
            messagebox.showwarning("Input Error", "Please enter an Item ID.")
            return

        try:
            change = int(quantity_change)
        except ValueError:
            messagebox.showwarning("Input Error", "Quantity must be a whole number.")
            return

        # --- Crucial Check: Prevent removing more than available ---
        if change < 0:
            current_inventory = self.blockchain.get_inventory()
            if current_inventory is None: # Blockchain invalid
                 self.status_label.config(text="Status: Error - Cannot validate stock.")
                 return
            current_stock = current_inventory.get(item_id, 0)
            if current_stock + change < 0:
                 messagebox.showerror("Stock Error", f"Cannot remove {-change} units of '{item_id}'. Only {current_stock} available.")
                 return

        transaction = {'item_id': item_id, 'change': change}
        if self.blockchain.add_transaction(transaction):
            # Mine immediately after adding a transaction for simplicity
            # Alternatively, you could have a separate "Mine" button
            mined = self.blockchain.mine_pending_transactions()
            if mined:
                 self.status_label.config(text=f"Status: Block mined. Stock for '{item_id}' updated.")
                 self.update_inventory_display() # Update display
                 self.item_id_entry.delete(0, tk.END) # Clear inputs
                 self.quantity_entry.delete(0, tk.END)
            else:
                 # Should not happen if add_transaction succeeded, but defensive
                 self.status_label.config(text="Status: Transaction added, waiting to be mined.")
        else:
            messagebox.showerror("Error", "Failed to add transaction to pending list.")
            self.status_label.config(text="Status: Error adding transaction.")


    def add_stock(self):
        item_id = self.item_id_entry.get().strip().upper() # Standardize ID case
        quantity = self.quantity_entry.get().strip()
        if not quantity:
            messagebox.showwarning("Input Error", "Please enter a quantity to add.")
            return
        try:
             qty_val = int(quantity)
             if qty_val <= 0:
                  messagebox.showwarning("Input Error", "Quantity to add must be positive.")
                  return
        except ValueError:
             messagebox.showwarning("Input Error", "Quantity must be a whole number.")
             return

        self._add_transaction(item_id, qty_val)


    def remove_stock(self):
        item_id = self.item_id_entry.get().strip().upper() # Standardize ID case
        quantity = self.quantity_entry.get().strip()

        if not quantity:
            messagebox.showwarning("Input Error", "Please enter a quantity to remove.")
            return
        try:
            qty_val = int(quantity)
            if qty_val <= 0:
                 messagebox.showwarning("Input Error", "Quantity to remove must be positive.")
                 return
        except ValueError:
             messagebox.showwarning("Input Error", "Quantity must be a whole number.")
             return

        # Pass quantity as negative to transaction helper
        self._add_transaction(item_id, -qty_val)

    # def mine_and_refresh(self):
    #     """Explicitly mines pending transactions and refreshes display."""
    #     mined = self.blockchain.mine_pending_transactions()
    #     if mined:
    #         self.status_label.config(text="Status: Pending transactions mined.")
    #         self.update_inventory_display()
    #     else:
    #          self.status_label.config(text="Status: No pending transactions to mine.")

    def update_inventory_display(self):
        """Fetch inventory from blockchain and update text area."""
        self.inventory_display.config(state='normal') # Enable writing
        self.inventory_display.delete('1.0', tk.END) # Clear previous content

        inventory = self.blockchain.get_inventory()

        if inventory is None: # Indicates failed blockchain validation
             self.inventory_display.insert(tk.END, "Error: Could not validate blockchain.\nInventory data unavailable.")
             self.status_label.config(text="Status: Error - Blockchain invalid.")
        elif not inventory:
            self.inventory_display.insert(tk.END, "Warehouse is currently empty.")
            self.status_label.config(text="Status: Inventory refreshed.")
        else:
            header = f"{'Item ID':<20} {'Quantity':<10}\n"
            separator = "-" * 31 + "\n"
            self.inventory_display.insert(tk.END, header)
            self.inventory_display.insert(tk.END, separator)
            # Sort items
            for item_id, quantity in sorted(inventory.items()):
                 # Only show items with stock > 0
                 if quantity > 0:
                    self.inventory_display.insert(tk.END, f"{item_id:<20} {quantity:<10}\n")
            self.status_label.config(text="Status: Inventory refreshed.")

        self.inventory_display.config(state='disabled') # Disable editing


# --- Main Execution ---

if __name__ == "__main__":
    # --- Configuration ---
    BLOCKCHAIN_FILE = "warehouse_inventory_chain.pkl" # Name of file
    MINING_DIFFICULTY = 2 # Number of leading zeros

    # Initialize blockchain (loads existing or creates new)
    inventory_blockchain = Blockchain(difficulty=MINING_DIFFICULTY, chain_file=BLOCKCHAIN_FILE)

    # Set up and run the GUI
    main_window = tk.Tk()
    app = InventoryApp(main_window, inventory_blockchain)
    main_window.mainloop()

    # Optional: Final save on clean exit (though save happens after mining)
    # inventory_blockchain.save_chain()
    print("Application closed.")
