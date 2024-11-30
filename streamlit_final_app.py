import streamlit as st
from fetch_case_data_and_summarize import IKApi, query_ai_model  # Replace with your actual import

# In-memory user data
users = {
    "admin": {"password": "admin123", "approved": True, "is_admin": True},  # Predefined admin credentials
}
if "pending_users" not in st.session_state:
    st.session_state.pending_users = {}  # Pending users for admin approval

# Initialize IKApi (replace with your own implementation)
ikapi = IKApi(maxpages=5)

# Initialize session state
if "authentication_status" not in st.session_state:
    st.session_state.authentication_status = False
    st.session_state.username = None
    st.session_state.is_admin = False


# Admin Panel for approving users
def admin_panel():
    st.subheader("Admin Panel")
    if st.session_state.is_admin:
        if st.session_state.pending_users:
            st.info("Pending User Approvals:")
            for user, details in list(st.session_state.pending_users.items()):
                st.write(f"User: {user}")
                if st.button(f"Approve {user}", key=f"approve_{user}"):
                    users[user] = {"password": details["password"], "approved": True, "is_admin": False}
                    del st.session_state.pending_users[user]
                    st.success(f"Approved user: {user}")
        else:
            st.info("No users pending approval.")
    else:
        st.error("Only admins can access this page.")


# Main app content (query and insights)
def main_app():
    st.title("Legal Case Analysis Assistant")
    st.markdown("This app provides detailed insights from legal case summaries.")

    query = st.text_input("Enter your legal query (e.g., 'road accident cases'):")
    if st.button("Analyze"):
        if not query.strip():
            st.warning("Please enter a valid query.")
        else:
            st.info("Fetching related cases...")
            doc_ids = ikapi.fetch_all_docs(query)

            if not doc_ids:
                st.error("No related documents found for your query.")
            else:
                st.success(f"Found {len(doc_ids)} related documents. Processing summaries...")

                all_summaries = []
                for docid in doc_ids[:2]:  # Process only the first 2 case documents
                    case_details = ikapi.fetch_doc(docid)

                    if not case_details:
                        st.warning(f"Failed to fetch details for document ID: {docid}")
                        continue

                    title = case_details.get("title", "No Title")
                    main_text = case_details.get("doc", "")
                    cleaned_text = ikapi.clean_text(main_text)
                    chunks = list(ikapi.split_text_into_chunks(cleaned_text))
                    summaries = []

                    for chunk in chunks:
                        summary = ikapi.summarize(chunk)
                        if summary:
                            summaries.append(summary)

                    final_summary = " ".join(summaries)
                    all_summaries.append(f"Title: {title}\nSummary: {final_summary}")

                combined_summary = "\n\n".join(all_summaries)
                st.subheader("Summarized Case Details")
                st.text_area("Summaries", combined_summary, height=300)

                st.info("Generating insights from summaries...")
                insights = query_ai_model(query, combined_summary)
                st.subheader("AI Insights and Analysis")
                st.write(insights)


# User registration
def register_user():
    st.subheader("Register")
    new_username = st.text_input("Choose a username")
    new_password = st.text_input("Choose a password", type="password")
    if st.button("Register"):
        if new_username in users or new_username in st.session_state.pending_users:
            st.error("Username already exists!")
        elif not new_username.strip() or not new_password.strip():
            st.warning("Username and password cannot be empty!")
        else:
            st.session_state.pending_users[new_username] = {"password": new_password}
            st.success("Registration successful! Wait for admin approval.")


# User login
def login_user():
    st.subheader("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username in users and users[username]["password"] == password:
            if users[username]["approved"]:
                st.session_state.authentication_status = True
                st.session_state.username = username
                st.session_state.is_admin = users[username]["is_admin"]
                st.success(f"Welcome, {username}!")
            else:
                st.error("Your account is not approved yet. Please wait for admin approval.")
        else:
            st.error("Invalid username or password.")


# Logout function
def logout():
    st.session_state.authentication_status = False
    st.session_state.username = None
    st.session_state.is_admin = False
    st.success("You have been logged out.")


# Sidebar menu
menu = st.sidebar.selectbox("Menu", ["Login", "Register", "Admin Panel", "Main App", "Logout"])

if menu == "Register":
    if not st.session_state.authentication_status:
        register_user()
    else:
        st.warning("You are already logged in!")

elif menu == "Login":
    if not st.session_state.authentication_status:
        login_user()
    else:
        st.warning("You are already logged in!")

elif menu == "Admin Panel":
    if st.session_state.authentication_status and st.session_state.is_admin:
        admin_panel()
    else:
        st.error("You must be an admin to access this page.")

elif menu == "Main App":
    if st.session_state.authentication_status:
        main_app()
    else:
        st.error("You must log in to access this page.")

elif menu == "Logout":
    if st.session_state.authentication_status:
        logout()
    else:
        st.warning("You are not logged in!")
