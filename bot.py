import os
import json
import sys
from datetime import datetime, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import threading
import time as time_module  # Import time module to avoid name clash with datetime.time
from telegram.error import TimedOut  # Import TimedOut error

# Function to read options.json and set bot's variables
def setup_options():
    global ADMIN_ID, INTERACTIONS_FOLDER, OFF_TIME_START_HOUR, OFF_TIME_END_HOUR

    try:
        with open("options.json", "r") as f:
            options = json.load(f)

        ADMIN_ID = options.get("ADMIN_ID", 0)
        INTERACTIONS_FOLDER = options.get("INTERACTIONS_FOLDER", "interactions")
        OFF_TIME_START_HOUR = options.get("OFF_TIME_START_HOUR", 20)
        OFF_TIME_END_HOUR = options.get("OFF_TIME_END_HOUR", 8)

    except FileNotFoundError:
        print("options.json not found. Using default values.")

# Default values for variables
ADMIN_ID = 0
INTERACTIONS_FOLDER = "interactions"
OFF_TIME_START_HOUR = 20  # 8 PM
OFF_TIME_END_HOUR = 8    # 8 AM

# Function to print a stylized "Bot started working" message
def print_start_message():
    print("\n" + " " * 10 +  "╔═══════════════════════════════╗ ")
    print(" " * 10 +         "║      Bot Started Working      ║ ")
    print(" " * 10 +         "╚═══════════════════════════════╝ ")
    print("\n")

# Function to log the message into a JSON file
def log_message(user_id, message):
    user_folder_path = os.path.join(INTERACTIONS_FOLDER, str(user_id))
    user_file_path = os.path.join(user_folder_path, "messages.json")

    # Create user folder if it doesn't exist
    os.makedirs(user_folder_path, exist_ok=True)

    # Prepare the timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Load existing data or create an empty list
    try:
        with open(user_file_path, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = []

    # Append the new message with a timestamp
    data.append({"timestamp": timestamp, "message": message})  # No encoding or decoding needed

    # Write the updated data back to the JSON file
    with open(user_file_path, "w") as f:
        json.dump(data, f, indent=4)

# Function to check if the current time is within the off-time period
def is_off_time():
    current_time = datetime.now().time()
    off_time_start = time(OFF_TIME_START_HOUR, 0)  # Create time object
    off_time_end = time(OFF_TIME_END_HOUR, 0)    # Create time object
    return off_time_start <= current_time <= off_time_end

# Command handler for the /start command
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Hello! I am Testicool bot. How can I assist you today?')

# Command handler for the /help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "Here are the commands you can use:\n"
        "/start - Start the conversation with the bot\n"
        "/help - Get a list of available commands\n"
        "/echo {message} - Echo back the message you send\n"
        "/admin - Access the admin panel (for authorized users)\n"
        )
    await update.message.reply_text(help_text)

# Handler for all messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    message = update.message.text

    # Ignore messages during off-time hours
    if is_off_time():
        print(f"Message from User ID: {username}({user_id}) ignored due to off-time period.")
        return

    # Log the message to file
    log_message(user_id, message)
    
    # Print the message to the console
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if username:
        print(f"[{timestamp}] User ID: {user_id}, Username: {username} sent message: {message}")
    else:
        print(f"[{timestamp}] User ID: {user_id} sent message: {message}")

    # Reply to the user's message
    await update.message.reply_text(f"You said: {message}") 

# Admin command handler
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global ADMIN_ID, INTERACTIONS_FOLDER, OFF_TIME_START_HOUR, OFF_TIME_END_HOUR
    user_id = update.message.from_user.id

    # Check if the user is authorized
    if user_id == ADMIN_ID:
        args = context.args
        if len(args) == 2:
            variable_name = args[0]
            value = args[1]
            
            # Validate variable name and value
            if variable_name in ["ADMIN_ID", "INTERACTIONS_FOLDER", "OFF_TIME_START_HOUR", "OFF_TIME_END_HOUR"]:
                try:
                    if variable_name == "ADMIN_ID":
                        value = int(value)  # Ensure admin id is an integer
                    elif variable_name == "INTERACTIONS_FOLDER":
                        value = str(value)  # Ensure folder name is a string
                    elif variable_name in ["OFF_TIME_START_HOUR", "OFF_TIME_END_HOUR"]:
                        value = int(value)  # Ensure hours are integers
                    
                    # Update the global variable
                    globals()[variable_name] = value
                    
                    # Update options.json
                    update_options_file(variable_name, value)

                    await update.message.reply_text(f"Successfully updated {variable_name} to {value}")
                except ValueError:
                    await update.message.reply_text("Invalid value provided. Please enter a valid value.")
            else:
                await update.message.reply_text("Invalid variable name. Allowed variables are: INTERACTIONS_FOLDER, OFF_TIME_START_HOUR, OFF_TIME_END_HOUR")
        else:
            await update.message.reply_text("Usage: /admin <variable_name> <value>")
    else:
        await update.message.reply_text("You are not authorized to use this command.")

# Helper function to update options.json
def update_options_file(variable_name, value):
    try:
        with open("options.json", "r") as f:
            options = json.load(f)
        options[variable_name] = value
        with open("options.json", "w") as f:
            json.dump(options, f, indent=4)
    except FileNotFoundError:
        print("options.json not found. Creating a new file.")
        with open("options.json", "w") as f:
            json.dump({variable_name: value}, f, indent=4)
    except json.JSONDecodeError:
        print("Error decoding options.json. Please ensure it's a valid JSON file.")

# Function to keep the bot alive by pinging a website and re-running the bot in case of timeout
def keep_alive():
    while True:
        try:
            os.system("ping -c 1 google.com > nul")
            time_module.sleep(300)
        except:
            print("Bot timed out. Restarting...")
            os.system(f"python {sys.argv[0]} {sys.argv[1]} {sys.argv[2]}")
            break

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python bot.py <BOT_TOKEN> <ADMIN_ID>")
        sys.exit(1)

    token = sys.argv[1]
    #ADMIN_ID = int(sys.argv[2])  # Get admin ID from command-line argument

    # Show start message
    print_start_message()

    # Setup options from options.json
    setup_options()
    
    # Set terminal title
    os.system(f"title {os.path.basename(__file__)}")

    # Start the keep-alive thread
    keep_alive_thread = threading.Thread(target=keep_alive)
    keep_alive_thread.daemon = True  # Make the thread a daemon so it doesn't block the bot from exiting
    keep_alive_thread.start()

    # Start the bot
    app = ApplicationBuilder().token(token).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    try:
        app.run_polling()
    except TimedOut:
        print("Bot timed out. Restarting...")
        os.system(f"python {sys.argv[0]} {sys.argv[1]} {sys.argv[2]}")
