import streamlit as st
from fetch_case_data_and_summarize import IKApi, query_ai_model

# In-memory user data storage
users = {
    "admin": {"password": "admin123", "approved": True, "is_admin": True},
}
pending_users = {}  # Store unapproved users

# Initialize session state for login status
if "authentication_status" not in st.session_state:
    st.session_state.authentication_status = None
    st.session_state.username = None

# In-memory IKApi for case data retrieval and summarization
ikapi = IKApi(maxpages=5)

# Function for Admin Panel
def admin_panel():
    st.subheader("Admin Panel")
    admin_username = st.text_input("Admin Username")
    admin_password = st.text_input("Admin Password", type="password")
    
    if st.button("Login as Admin"):
        if admin_username in users and users[admin_username]["is_admin"] and users[admin_username]["password"] == admin_password:
            st.session_state.authentication_status = True
            st.session_state.username = admin_username
            st.success("Admin logged in successfully!")
        else:
            st.error("Invalid admin credentials.")

    # Approve users
    if st.session_state.authentication_status and st.session_state.username == "admin":
        st.subheader("Pending User Approvals")
        if not pending_users:
            st.info("No pending users.")
        else:
            for pending_user, details in list(pending_users.items()):
                st.write(f"User: {pending_user}")
                if st.button(f"Approve {pending_user}"):
                    users[pending_user] = details
                    users[pending_user]["approved"] = True
                    pending_users.pop(pending_user)
                    st.success(f"Approved user: {pending_user}")

# Function for user query and insights
def user_query_and_insights():
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

# Login/Registration Interface
menu = st.sidebar.selectbox("Menu", ["Login", "Register", "Admin Panel"])

if menu == "Register":
    st.subheader("Register")
    new_username = st.text_input("Enter a username")
    new_password = st.text_input("Enter a password", type="password")
    if st.button("Register"):
        if new_username in users or new_username in pending_users:
            st.error("Username already exists!")
        elif new_username.strip() == "" or new_password.strip() == "":
            st.warning("Username and password cannot be empty!")
        else:
            pending_users[new_username] = {"password": new_password, "approved": False}
            st.success("Registration successful! Wait for admin approval.")

elif menu == "Login":
    st.subheader("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username in users and users[username]["password"] == password:
            if users[username]["approved"]:
                st.session_state.authentication_status = True
                st.session_state.username = username
                st.success(f"Welcome, {username}!")
            else:
                st.error("Your account is not approved yet. Please wait for admin approval.")
        else:
            st.error("Invalid username or password.")

# Admin Panel
elif menu == "Admin Panel":
    admin_panel()

# Logged-in content for approved users
if st.session_state.authentication_status and st.session_state.username != "admin":
    user_query_and_insights()

# Admin functionality
if st.session_state.authentication_status and st.session_state.username == "admin":
    st.sidebar.subheader("Admin Dashboard")
    st.sidebar.write("You can manage users here.")
