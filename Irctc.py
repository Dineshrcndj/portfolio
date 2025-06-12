import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import pytesseract
from PIL import Image
import time
import random
import datetime
import ntplib
import requests
from twilio.rest import Client  # For SMS alerts
import os
from fake_useragent import UserAgent

# ======================
# CONFIGURATION SECTION
# ======================
class Config:
    # Account Details
    USERNAME = "your_irctc_id"
    PASSWORD = "your_password"
    
    # Journey Details
    FROM_STATION = "DELHI (DEL)"
    TO_STATION = "MUMBAI (BOM)"
    TRAIN_NUMBER = "12345"  # Example Rajdhani
    DOJ = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%d-%m-%Y")  # Tomorrow's date
    QUOTA_PRIORITY = ["TATKAL", "PREMIUM TATKAL"]  # Order of quota preference
    CLASS_PRIORITY = ["3A", "2A", "SL"]  # Order of class preference
    
    # Passenger Details
    PASSENGERS = [
        {"name": "John Doe", "age": "30", "gender": "M", "berth": "Lower"}
    ]
    
    # Payment Details
    PAYMENT_METHOD = "PAYTM"  # Options: PAYTM, CREDIT_CARD, DEBIT_CARD, UPI
    
    # Notification Settings
    TWILIO_SID = "your_twilio_sid"
    TWILIO_AUTH_TOKEN = "your_twilio_token"
    TWILIO_PHONE = "+1234567890"
    YOUR_PHONE = "+919876543210"
    
    # Advanced Settings
    USE_PROXY = False
    PROXY_LIST = ["103.216.144.1:8080", "45.167.124.5:999"]
    USE_CAPTCHA_SERVICE = False  # Set True if using 2Captcha/other service
    CAPTCHA_API_KEY = "your_2captcha_key"
    MAX_RETRIES = 3
    HUMANIZE_DELAYS = True

# ======================
# UTILITY FUNCTIONS
# ======================
class Utils:
    @staticmethod
    def get_ist_time():
        """Get precise Indian Standard Time using NTP"""
        try:
            client = ntplib.NTPClient()
            response = client.request('in.pool.ntp.org')
            return datetime.datetime.fromtimestamp(response.tx_time)
        except:
            return datetime.datetime.now() + datetime.timedelta(minutes=330)  # IST fallback

    @staticmethod
    def human_delay(min_sec=0.5, max_sec=2.0):
        """Random delay to mimic human behavior"""
        if Config.HUMANIZE_DELAYS:
            time.sleep(random.uniform(min_sec, max_sec))

    @staticmethod
    def human_type(element, text, speed=0.1):
        """Type text with human-like delays"""
        for char in text:
            element.send_keys(char)
            Utils.human_delay(speed/2, speed)

    @staticmethod
    def solve_captcha(driver):
        """CAPTCHA solving with fallback options"""
        if Config.USE_CAPTCHA_SERVICE:
            try:
                from twocaptcha import TwoCaptcha
                captcha_img = driver.find_element(By.CLASS_NAME, "captcha-img")
                captcha_img.screenshot("captcha.png")
                solver = TwoCaptcha(Config.CAPTCHA_API_KEY)
                result = solver.normal('captcha.png')
                return result['code']
            except Exception as e:
                print(f"CAPTCHA service failed: {e}")
        
        # Fallback to manual solving
        input("⚠️ Please solve CAPTCHA manually and press Enter to continue...")
        return "MANUAL_ENTRY"

    @staticmethod
    def send_sms_alert(message):
        """Send booking status via SMS"""
        try:
            client = Client(Config.TWILIO_SID, Config.TWILIO_AUTH_TOKEN)
            client.messages.create(
                body=message,
                from_=Config.TWILIO_PHONE,
                to=Config.YOUR_PHONE
            )
        except Exception as e:
            print(f"Failed to send SMS: {e}")

    @staticmethod
    def save_ticket(driver):
        """Download and save ticket PDF"""
        try:
            ticket_url = driver.find_element(By.LINK_TEXT, "Download Ticket").get_attribute("href")
            response = requests.get(ticket_url)
            filename = f"IRCTC_Ticket_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            with open(filename, "wb") as f:
                f.write(response.content)
            print(f"🎫 Ticket saved as {filename}")
            return filename
        except Exception as e:
            print(f"Failed to save ticket: {e}")
            return None

# ======================
# MAIN BOOKING CLASS
# ======================
class IRCTCAutomation:
    def __init__(self):
        self.driver = None
        self.wait = None
        self.actions = None
        self.retry_count = 0

    def initialize_browser(self):
        """Configure stealth browser with optimizations"""
        print("🚀 Initializing stealth browser...")
        
        options = uc.ChromeOptions()
        
        # Anti-detection measures
        ua = UserAgent()
        user_agent = ua.random
        options.add_argument(f"user-agent={user_agent}")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--start-maximized")
        
        # Proxy configuration
        if Config.USE_PROXY and Config.PROXY_LIST:
            proxy = random.choice(Config.PROXY_LIST)
            options.add_argument(f"--proxy-server={proxy}")
            print(f"🌐 Using proxy: {proxy}")
        
        # Initialize driver
        self.driver = uc.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 15)
        self.actions = ActionChains(self.driver)
        
        # Random mouse movements to appear human
        self.humanize_browser()

    def humanize_browser(self):
        """Perform random human-like actions"""
        print("🤖 Humanizing browser behavior...")
        for _ in range(3):
            self.actions.move_by_offset(
                random.randint(5, 15),
                random.randint(5, 15)
            ).perform()
            Utils.human_delay(0.1, 0.3)

    def login(self):
        """Handle IRCTC login with CAPTCHA"""
        print("🔐 Attempting login...")
        
        self.driver.get("https://www.irctc.co.in/nget/train-search")
        Utils.human_delay(2, 4)
        
        # Handle initial popups
        try:
            self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[text()='OK']"))).click()
            Utils.human_delay(1, 2)
        except:
            pass
        
        # Fill credentials
        username = self.wait.until(EC.presence_of_element_located((By.ID, "userId")))
        Utils.human_type(username, Config.USERNAME)
        
        password = self.driver.find_element(By.ID, "pwd")
        Utils.human_type(password, Config.PASSWORD)
        Utils.human_delay(0.5, 1)
        
        # Solve CAPTCHA
        captcha_code = Utils.solve_captcha(self.driver)
        self.driver.find_element(By.ID, "captcha").send_keys(captcha_code)
        Utils.human_delay(0.5, 1)
        
        # Submit login
        self.driver.find_element(By.XPATH, "//button[text()='SIGN IN']").click()
        Utils.human_delay(3, 5)
        
        # Verify login
        try:
            self.wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(text(),'Book Ticket')]")))
            print("✅ Login successful")
            return True
        except:
            print("❌ Login failed")
            return False

    def wait_for_tatkal_window(self):
        """Precise timing for Tatkal window opening"""
        print("⏳ Waiting for Tatkal window (10:00 AM sharp)...")
        
        while True:
            current_time = Utils.get_ist_time().time()
            if current_time >= datetime.time(9, 59, 55):
                break
            time.sleep(0.1)
        
        # Final countdown
        for i in range(5, 0, -1):
            print(f"⏱️ Starting in {i} seconds...")
            time.sleep(1)
        
        print("🚀 Tatkal window open! Executing booking...")

    def search_trains(self):
        """Search for available trains with retry logic"""
        print("🔍 Searching for trains...")
        
        # Open new tab for fresh session
        self.driver.execute_script("window.open('https://www.irctc.co.in/nget/train-search')")
        self.driver.switch_to.window(self.driver.window_handles[-1])
        Utils.human_delay(2, 3)
        
        # Fill journey details
        origin = self.wait.until(EC.presence_of_element_located((By.ID, "origin")))
        Utils.human_type(origin, Config.FROM_STATION)
        Utils.human_delay(0.2, 0.5)
        
        destination = self.driver.find_element(By.ID, "destination")
        Utils.human_type(destination, Config.TO_STATION)
        Utils.human_delay(0.2, 0.5)
        
        # Set date
        self.driver.execute_script(f"document.getElementById('journeyDate').value = '{Config.DOJ}';")
        Utils.human_delay(0.5, 1)
        
        # Try different quotas
        for quota in Config.QUOTA_PRIORITY:
            try:
                quota_dropdown = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//div[@aria-label='Quota']")))
                quota_dropdown.click()
                Utils.human_delay(0.2, 0.5)
                
                self.driver.find_element(By.XPATH, f"//span[text()='{quota}']").click()
                Utils.human_delay(0.5, 1)
                print(f"🔁 Trying {quota} quota...")
                break
            except:
                continue
        
        # Search trains
        self.driver.find_element(By.XPATH, "//button[contains(text(),'Search')]").click()
        Utils.human_delay(2, 3)
        
        return True

    def select_train(self):
        """Select train with class availability check"""
        print("🚆 Selecting train with available classes...")
        start_time = time.time()
        timeout = 120  # 2 minutes timeout
        
        while time.time() - start_time < timeout:
            try:
                # Find our train
                train_xpath = f"//div[contains(@class,'train-available') and contains(.,'{Config.TRAIN_NUMBER}')]"
                train = self.wait.until(EC.presence_of_element_located((By.XPATH, train_xpath)))
                
                # Check for available classes in priority order
                for class_type in Config.CLASS_PRIORITY:
                    try:
                        class_xpath = f".//td[contains(@class,'{class_type}')]//span[contains(text(),'Available')]"
                        train.find_element(By.XPATH, class_xpath)
                        print(f"🎫 Found available {class_type} class")
                        train.find_element(By.XPATH, f".//td[contains(@class,'{class_type}')]").click()
                        return True
                    except:
                        continue
                
                # If no classes found, refresh
                print("🔄 No available classes, refreshing...")
                self.driver.refresh()
                Utils.human_delay(1, 2)
            except:
                print("🔄 Train not found, refreshing...")
                self.driver.refresh()
                Utils.human_delay(1, 2)
        
        raise Exception("❌ No available trains found within timeout")

    def fill_passenger_details(self):
        """Fill passenger information"""
        print("👥 Filling passenger details...")
        
        self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[text()='Book Now']"))).click()
        Utils.human_delay(2, 3)
        
        for i, passenger in enumerate(Config.PASSENGERS):
            # Fill name
            name_field = self.wait.until(EC.presence_of_element_located((By.ID, f"passengerName{i}")))
            Utils.human_type(name_field, passenger["name"])
            Utils.human_delay(0.1, 0.3)
            
            # Fill age
            age_field = self.driver.find_element(By.ID, f"passengerAge{i}")
            Utils.human_type(age_field, passenger["age"])
            Utils.human_delay(0.1, 0.3)
            
            # Select gender
            gender_dropdown = self.driver.find_element(By.ID, f"passengerGender{i}")
            gender_dropdown.click()
            Utils.human_delay(0.1, 0.3)
            self.driver.find_element(By.XPATH, f"//li[text()='{passenger['gender']}']").click()
            Utils.human_delay(0.1, 0.3)
            
            # Select berth preference if specified
            if "berth" in passenger:
                berth_dropdown = self.driver.find_element(By.ID, f"passengerBerthChoice{i}")
                berth_dropdown.click()
                Utils.human_delay(0.1, 0.3)
                self.driver.find_element(By.XPATH, f"//li[contains(text(),'{passenger['berth']}')]").click()
                Utils.human_delay(0.1, 0.3)
        
        return True

    def make_payment(self):
        """Complete payment process"""
        print("💳 Proceeding to payment...")
        
        self.wait.until(EC.element_to_be_clickable((By.ID, "paymentSubmit"))).click()
        Utils.human_delay(3, 5)
        
        # Handle payment gateway
        try:
            self.wait.until(EC.frame_to_be_available_and_switch_to_it((By.XPATH, "//iframe[contains(@title,'Payment')]")))
            Utils.human_delay(1, 2)
            
            # Select payment method
            payment_method_xpath = f"//label[contains(text(),'{Config.PAYMENT_METHOD}')]"
            self.wait.until(EC.element_to_be_clickable((By.XPATH, payment_method_xpath))).click()
            Utils.human_delay(0.5, 1)
            
            # Submit payment
            self.driver.find_element(By.ID, "makePayment").click()
            Utils.human_delay(5, 8)  # Extra delay for payment processing
            
            # Switch back to main window
            self.driver.switch_to.default_content()
            
            # Verify booking success
            self.wait.until(EC.presence_of_element_located((By.XPATH, "//h2[contains(text(),'Booking Successful')]")))
            print("✅ Payment successful! Booking confirmed.")
            return True
        except Exception as e:
            print(f"❌ Payment failed: {str(e)}")
            return False

    def complete_booking(self):
        """Finalize booking and download ticket"""
        print("🎉 Finalizing booking...")
        
        # Download ticket
        ticket_file = Utils.save_ticket(self.driver)
        
        # Send success notification
        message = f"IRCTC Tatkal Booking Successful! PNR: {self.get_pnr_number()}"
        Utils.send_sms_alert(message)
        
        return True

    def get_pnr_number(self):
        """Extract PNR from booking confirmation"""
        try:
            pnr_element = self.wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(text(),'PNR No')]/following-sibling::div")))
            return pnr_element.text.strip()
        except:
            return "UNKNOWN"

    def run(self):
        """Main execution flow with error handling"""
        try:
            # Initialize with retries
            while self.retry_count < Config.MAX_RETRIES:
                try:
                    self.initialize_browser()
                    
                    # Phase 1: Pre-Tatkal Login (before 10 AM)
                    if not self.login():
                        raise Exception("Login failed")
                    
                    # Phase 2: Tatkal Window Timing
                    self.wait_for_tatkal_window()
                    
                    # Phase 3: Train Search & Selection
                    if not self.search_trains():
                        raise Exception("Train search failed")
                    
                    if not self.select_train():
                        raise Exception("Train selection failed")
                    
                    # Phase 4: Passenger Details
                    if not self.fill_passenger_details():
                        raise Exception("Passenger details failed")
                    
                    # Phase 5: Payment
                    if not self.make_payment():
                        raise Exception("Payment failed")
                    
                    # Phase 6: Completion
                    if not self.complete_booking():
                        raise Exception("Completion failed")
                    
                    # Success - break retry loop
                    break
                
                except Exception as e:
                    self.retry_count += 1
                    print(f"⚠️ Attempt {self.retry_count} failed: {str(e)}")
                    
                    if self.retry_count < Config.MAX_RETRIES:
                        print("♻️ Retrying...")
                        self.driver.quit()
                        Utils.human_delay(5, 10)  # Delay between retries
                    else:
                        raise Exception("Max retries exceeded")
        
        except Exception as e:
            print(f"❌ Fatal error: {str(e)}")
            Utils.send_sms_alert(f"IRCTC Booking Failed: {str(e)}")
            
            # Save screenshot for debugging
            screenshot_name = f"error_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            self.driver.save_screenshot(screenshot_name)
            print(f"📸 Saved error screenshot as {screenshot_name}")
        
        finally:
            if self.driver:
                self.driver.quit()

# ======================
# EXECUTION
# ======================
if __name__ == "__main__":
    print("""
    ██╗██╗██████╗ ████████╗ ██████╗     ████████╗ █████╗ ████████╗██╗  ██╗ █████╗ ██╗     
    ██║██║██╔══██╗╚══██╔══╝██╔════╝     ╚══██╔══╝██╔══██╗╚══██╔══╝██║ ██╔╝██╔══██╗██║     
    ██║██║██████╔╝   ██║   ██║  ███╗       ██║   ███████║   ██║   █████╔╝ ███████║██║     
    ██║██║██╔══██╗   ██║   ██║   ██║       ██║   ██╔══██║   ██║   ██╔═██╗ ██╔══██║██║     
    ██║██║██║  ██║   ██║   ╚██████╔╝       ██║   ██║  ██║   ██║   ██║  ██╗██║  ██║███████╗
    ╚═╝╚═╝╚═╝  ╚═╝   ╚═╝    ╚═════╝        ╚═╝   ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝
    """)
    
    automation = IRCTCAutomation()
    automation.run()
