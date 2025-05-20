from playwright.sync_api import sync_playwright
import time

def login_to_petpoint():
    with sync_playwright() as p:
        # Launch the browser
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        try:
            print("Navigating to PetPoint login page...")
            page.goto("https://sms.petpoint.com/sms3/forms/signinout.aspx")
            
            # Wait for the page to load
            page.wait_for_load_state('networkidle')
            time.sleep(2)
            
            print("Looking for Shelter ID input...")
            # Wait for and fill in the Shelter ID
            page.fill("#LoginShelterId", "USNY9")
            time.sleep(1)
            
            print("Clicking Next button...")
            # Try clicking the Next button
            page.click("#LoginShelterIDButton")
            time.sleep(2)
            
            print("Looking for Username input...")
            # Wait for and fill in the Username
            page.fill("#LoginUsername", "zaks")
            time.sleep(1)
            
            print("Looking for Password input...")
            # Fill in the Password
            page.fill("#LoginPassword", "Gillian666!")
            time.sleep(1)
            
            print("Clicking Login button...")
            # Click the Login button
            page.click("#LoginLoginButton")
            
            # Wait for login to complete
            time.sleep(5)
            
            print("Successfully logged in to PetPoint!")
            
            # Keep the browser open for now
            input("Press Enter to close the browser...")
            
        except Exception as e:
            print(f"An error occurred: {str(e)}")
        finally:
            browser.close()

if __name__ == "__main__":
    login_to_petpoint() 