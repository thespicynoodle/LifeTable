import streamlit as st
from datetime import datetime
import time

def main():
    # Create space in the sidebar to push the time to the bottom
    st.sidebar.write("\n" * 10)  # Adjust the number of newlines to push the content down

    # Create a placeholder for the time at the bottom of the sidebar
    time_placeholder = st.sidebar.empty()

    # Function to update time in the sidebar
    def update_time():
        while True:
            current_time = datetime.now().strftime("%H:%M:%S")
            time_placeholder.markdown(f"**Current Time:** {current_time}")
            time.sleep(1)

    # Run the time updater function in a separate thread
    import threading
    time_thread = threading.Thread(target=update_time)
    time_thread.daemon = True
    time_thread.start()

    # Main content of the app
    st.title("Research Mutt")
    st.write("Welcome to the search assistant app")
    st.write("Use the navigation on the left to browse different pages.")

    st.write("** NEEED TO ADD DATA UNTIL 1991 TO SUPABASE**")

    
    st.write(update_time())
if __name__ == "__main__":
    main()
