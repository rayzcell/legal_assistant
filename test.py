import http.client
import json
import urllib.parse

def fetch_case_data(api_token, query):
    """
    Fetches case data based on a search query and returns only the title and detailed text.
    
    Parameters:
    - api_token: str, your API token for authentication.
    - query: str, the search query for retrieving case data.
    
    Returns:
    - List of dictionaries with keys 'title' and 'text' containing the case title and detailed text.
    """
    conn = http.client.HTTPSConnection("api.indiankanoon.org")
    headers = {"Authorization": f"Bearer {api_token}"}
    
    # Encode the query to handle spaces and special characters
    encoded_query = urllib.parse.quote(query)
    url = f"/api/v1/search/?query={encoded_query}&format=json"

    try:
        conn.request("GET", url, headers=headers)
        response = conn.getresponse()
        
        # Check if the response status is OK
        if response.status != 200:
            print(f"HTTP error {response.status}: {response.reason}")
            return None

        # Read and decode the response
        data = response.read().decode("utf-8")

        # Debugging step: Print response data if unexpected results occur
        print(f"Raw response data:\n{data}\n")
        
        # Check if the data is empty or not JSON-formatted
        if not data.strip():
            print("Empty response received.")
            return None
        
        # Parse JSON
        case_data = json.loads(data)
        
        # Extract only the title and detailed text for each case
        cases = []
        if "results" in case_data:
            for case in case_data["results"]:
                title = case.get("title", "")
                text = case.get("text", "")
                cases.append({"title": title, "text": text})
                
                # Debugging: Print extracted information for verification
                print("\nCase title:", title)
                print("Case text preview:", text[:300], "...")  # Preview of the text
            
        conn.close()
        return cases

    except http.client.HTTPException as e:
        print(f"HTTP error occurred: {e}")
    except json.JSONDecodeError as e:
        print(f"JSON decode error occurred: {e}. Response may not be in JSON format.")
    except Exception as e:
        print(f"An error occurred: {e}")

def format_for_llm(cases):
    """
    Formats the cases for direct input into an LLM for summarization.
    
    Parameters:
    - cases: list of dictionaries with 'title' and 'text' keys.
    
    Returns:
    - Formatted string with each case in a suitable format for summarization.
    """
    formatted_text = []
    for case in cases:
        formatted_text.append(f"Title: {case['title']}\nText: {case['text']}\n\n---\n")
    
    return "\n".join(formatted_text)

# Example usage
api_token = "6ac69313684dfe82332e7949d640bea1dc931272"  # Replace with your actual token
query = "land dispute"  # Replace with your query

# Fetch and format cases
case_data = fetch_case_data(api_token, query)
if case_data:
    formatted_text_for_llm = format_for_llm(case_data)
    
    # Output for review or further processing
    print("\nFormatted text for LLM input:\n")
    print(formatted_text_for_llm)
else:
    print("No data fetched from the API.")
