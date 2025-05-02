import tkinter as tk
from tkinter import messagebox, ttk
import psycopg2
import datetime
import ssl

# --- PostgreSQL Database Connection ---
def get_db_config():
    """Return working connection parameters using Supabase pooler"""
    return {
        'host': 'aws-0-ap-south-1.pooler.supabase.com',
        'user': 'postgres.xvjrzrhhirlkxxpieijq',
        'password': 'iambatman69',
        'port': 6543,
        'database': 'postgres',
        'sslmode': 'require',
        'connect_timeout': 5
    }

def connect_to_database():
    try:
        conn = psycopg2.connect(**get_db_config())
        return conn
    except Exception as e:
        messagebox.showerror("Database Error", f"Connection failed: {e}")
        return None

# --- Safe Query Execution ---
def safe_db_execute(cursor, query, params=None, fetch=False):
    try:
        cursor.execute(query, params)
        if fetch:
            result = cursor.fetchall()
        cursor.connection.commit()
        return result if fetch else None
    except Exception as e:
        cursor.connection.rollback()
        messagebox.showerror("Database Error", str(e))
        return None

# --- Auction App GUI ---
class AuctionApp:
    def __init__(self, root):
        self.announced_items = set()
        self.root = root
        self.root.title("Auction System")
        self.root.geometry("1000x650")

        self.db_connection = connect_to_database()
        if not self.db_connection:
            self.root.destroy()
            return

        self.cursor = self.db_connection.cursor()
        self.current_user = None

        self.show_login_screen()

    def clear_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def show_login_screen(self):
        self.clear_screen()
        frame = tk.Frame(self.root)
        frame.pack(pady=50)

        tk.Label(frame, text="Login", font=("Arial", 24, "bold")).pack(pady=10)

        tk.Label(frame, text="Username:").pack()
        self.username_entry = tk.Entry(frame, width=30)
        self.username_entry.pack(pady=5)

        tk.Label(frame, text="Password:").pack()
        self.password_entry = tk.Entry(frame, show="*", width=30)
        self.password_entry.pack(pady=5)

        tk.Button(frame, text="Login", width=15, command=self.login).pack(pady=10)
        tk.Button(frame, text="Register", width=15, command=self.register).pack()

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        result = safe_db_execute(
            self.cursor,
            "SELECT id FROM user_accounts WHERE username = %s AND password = %s",
            (username, password),
            fetch=True
        )
        if result:
            self.current_user = {'id': result[0][0], 'username': username}
            self.show_dashboard()
        else:
            messagebox.showerror("Login Failed", "Invalid credentials")

    def register(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        safe_db_execute(
            self.cursor,
            "INSERT INTO user_accounts (username, password) VALUES (%s, %s)",
            (username, password)
        )
        messagebox.showinfo("Success", "Registration successful. Please login.")

    def show_dashboard(self):
        self.clear_screen()

        top_frame = tk.Frame(self.root)
        top_frame.pack(fill="x")
        tk.Label(top_frame, text=f"Welcome, {self.current_user['username']}!", font=("Arial", 16)).pack(side="left", padx=20, pady=10)
        tk.Button(top_frame, text="Logout", command=self.logout).pack(side="right", padx=20)

        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=20)

        tk.Button(btn_frame, text="View Available Items", width=25, command=self.view_items).grid(row=0, column=0, padx=10, pady=10)
        tk.Button(btn_frame, text="Start Bidding", width=25, command=self.start_bidding_screen).grid(row=0, column=1, padx=10, pady=10)
        tk.Button(btn_frame, text="View All Bids", width=25, command=self.view_all_bids).grid(row=1, column=0, padx=10, pady=10)
        tk.Button(btn_frame, text="My Bids", width=25, command=self.view_my_bids).grid(row=1, column=1, padx=10, pady=10)

    def view_items(self):
        self.clear_screen()
        tk.Label(self.root, text="Available Items", font=("Arial", 18)).pack(pady=10)

        tree = ttk.Treeview(self.root, columns=("ID", "Name", "Description", "Price", "End Time"), show="headings")
        for col in tree["columns"]:
            tree.heading(col, text=col)
        tree.pack(fill="both", expand=True)

        items = safe_db_execute(
            self.cursor,
            "SELECT item_id, item_name, description, starting_price, bidding_end_time FROM auction_items WHERE is_available = 1",
            fetch=True
        )
        for item in items:
            tree.insert("", "end", values=item)

        tk.Button(self.root, text="Back", command=self.show_dashboard).pack(pady=10)

    def start_bidding_screen(self):
        self.clear_screen()
        tk.Label(self.root, text="Start Bidding", font=("Arial", 18)).pack(pady=10)

        self.bidding_tree = ttk.Treeview(
            self.root,
            columns=("ID", "Name", "Description", "Current Price", "Status", "Time Left"),
            show="headings"
        )
        for col in self.bidding_tree["columns"]:
            self.bidding_tree.heading(col, text=col)
        self.bidding_tree.pack(fill="both", expand=True)

        # Fetch items with timer and status
        items = safe_db_execute(
            self.cursor,
            """
            SELECT item_id,
                   item_name,
                   description,
                   starting_price,
                   CASE
                       WHEN bidding_end_time < now() THEN 'Bidding Ended'
                       ELSE 'Ongoing'
                       END AS status,
                   bidding_end_time
            FROM auction_items
            WHERE is_available = 1
            ORDER BY item_id
            """,
            fetch=True
        )

        for item in items:
            item_id, name, description, price, status, end_time = item
            if end_time:
                remaining_time = str(end_time - datetime.datetime.now(datetime.timezone.utc)).split('.')[0]

            else:
                remaining_time = "N/A"

            self.bidding_tree.insert(
                "", "end", iid=item_id,
                values=(item_id, name, description, f"₹{price:.2f}", status, remaining_time)
            )

        # Inputs
        tk.Label(self.root, text="Enter Item ID:").pack()
        self.bid_item_id_entry = tk.Entry(self.root)
        self.bid_item_id_entry.pack()

        tk.Label(self.root, text="Your Bid Amount:").pack()
        self.bid_amount_entry = tk.Entry(self.root)
        self.bid_amount_entry.pack()

        tk.Button(self.root, text="Place Bid", command=self.place_bid).pack(pady=10)
        tk.Button(self.root, text="Back", command=self.show_dashboard).pack()

        self.update_timer()

    def update_timer(self):
        for child in self.bidding_tree.get_children():
            values = self.bidding_tree.item(child)["values"]
            item_id = values[0]

            result = safe_db_execute(
                self.cursor,
                "SELECT bidding_end_time FROM auction_items WHERE item_id = %s",
                (item_id,),
                fetch=True
            )
            if result:
                end_time = result[0][0]
                now = datetime.datetime.now(datetime.timezone.utc)

                if end_time:
                    remaining = end_time - now
                    if remaining.total_seconds() <= 0:
                        updated_values = list(values)
                        updated_values[4] = "Bidding Ended"
                        updated_values[5] = "Ended"
                        self.bidding_tree.item(child, values=updated_values)

                        # ✅ Show popup only once
                        if item_id not in self.announced_items:
                            winner = safe_db_execute(
                                self.cursor,
                                """
                                SELECT u.username, b.bid_amount
                                FROM bids_table b
                                         JOIN user_accounts u ON b.bidder_id = u.id
                                WHERE b.item_id = %s
                                ORDER BY b.bid_amount DESC LIMIT 1
                                """,
                                (item_id,), fetch=True
                            )

                            if winner and winner[0]:
                                username, bid = winner[0]
                                messagebox.showinfo(
                                    "🏆 Auction Ended",
                                    f"Item ID {item_id}\nWinner: {username}\nBid: ₹{bid:.2f}"
                                )
                            else:
                                messagebox.showinfo(
                                    "🏆 Auction Ended",
                                    f"Item ID {item_id}\nNo bids were placed."
                                )

                            self.announced_items.add(item_id)
                    else:
                        time_str = str(remaining).split('.')[0]
                        updated_values = list(values)
                        updated_values[5] = time_str
                        self.bidding_tree.item(child, values=updated_values)

        self.root.after(1000, self.update_timer)

    def place_bid(self):
        try:
            item_id = int(self.bid_item_id_entry.get())
            amount = float(self.bid_amount_entry.get())
        except ValueError:
            messagebox.showerror("Invalid Input", "Enter valid numbers")
            return

        result = safe_db_execute(
            self.cursor,
            "SELECT MAX(bid_amount) FROM bids_table WHERE item_id = %s",
            (item_id,), fetch=True
        )
        highest = result[0][0] if result and result[0][0] else 0

        if amount <= highest:
            messagebox.showerror("Invalid Bid", f"Your bid must be higher than ₹{highest:.2f}")
            return

        safe_db_execute(
            self.cursor,
            "INSERT INTO bids_table (item_id, bidder_id, bid_amount, bid_time) VALUES (%s, %s, %s, %s)",
            (item_id, self.current_user['id'], amount, datetime.datetime.now())
        )

        messagebox.showinfo("Success", "Bid placed successfully!")
        self.show_dashboard()

    def view_all_bids(self):
        self.clear_screen()
        tk.Label(self.root, text="All Bids", font=("Arial", 18)).pack(pady=10)

        tree = ttk.Treeview(self.root, columns=("Item ID", "Bidder", "Amount", "Time"), show="headings")
        for col in tree["columns"]:
            tree.heading(col, text=col)
        tree.pack(fill="both", expand=True)

        bids = safe_db_execute(
            self.cursor,
            """
            SELECT b.item_id, u.username, b.bid_amount, b.bid_time
            FROM bids_table b
            JOIN user_accounts u ON b.bidder_id = u.id
            ORDER BY b.bid_time DESC
            """,
            fetch=True
        )
        for bid in bids:
            tree.insert("", "end", values=bid)

        tk.Button(self.root, text="Back", command=self.show_dashboard).pack(pady=10)

    def view_my_bids(self):
        self.clear_screen()
        tk.Label(self.root, text="My Bids", font=("Arial", 18)).pack(pady=10)

        tree = ttk.Treeview(self.root, columns=("Item ID", "Amount", "Time"), show="headings")
        for col in tree["columns"]:
            tree.heading(col, text=col)
        tree.pack(fill="both", expand=True)

        bids = safe_db_execute(
            self.cursor,
            "SELECT item_id, bid_amount, bid_time FROM bids_table WHERE bidder_id = %s ORDER BY bid_time DESC",
            (self.current_user['id'],), fetch=True
        )
        for bid in bids:
            tree.insert("", "end", values=bid)

        tk.Button(self.root, text="Back", command=self.show_dashboard).pack(pady=10)

    def logout(self):
        self.current_user = None
        self.show_login_screen()

if __name__ == '__main__':
    root = tk.Tk()
    app = AuctionApp(root)
    root.mainloop()
