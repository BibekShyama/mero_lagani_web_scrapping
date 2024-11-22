from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from datetime import datetime
import sys
import pandas as pd
from bs4 import BeautifulSoup
import os


def search(driver, date):
    """
    Searches for the floorsheet based on the given date.
    Date should be in mm/dd/yyyy format.
    """
    try:
        driver.get("https://merolagani.com/Floorsheet.aspx")
        
        # Locate the date input field and search button
        date_input = driver.find_element(By.XPATH, '/html/body/form/div[4]/div[4]/div/div/div[1]/div[4]/input')
        search_btn = driver.find_element(By.XPATH, '/html/body/form/div[4]/div[4]/div/div/div[2]/a[1]')

        # Enter the date and perform search
        date_input.clear()
        date_input.send_keys(date)
        search_btn.click()

        # Check for the "No data" message
        no_data_message = "//*[contains(text(), 'Could not find floorsheet matching the search criteria')]"
        if driver.find_elements(By.XPATH, no_data_message):
            print("No data found for the given search.")
            print("Aborting script ......")
            sys.exit()
        else:
            print("Search completed successfully.")
    except NoSuchElementException as e:
        print("Error: Element not found on the page.")
        print(f"Details: {e}")
    except TimeoutException as e:
        print("Error: Page load timeout.")
        print(f"Details: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


def get_page_table(driver, table_class):
    soup = BeautifulSoup(driver.page_source,'html')
    table = soup.find("table", {"class":table_class})
    tab_data = [[cell.text.replace('\r', '').replace('\n', '') for cell in row.find_all(["th","td"])]
                        for row in table.find_all("tr")]
    df = pd.DataFrame(tab_data)
    return df



def scrape_data(driver, date):
    start_time = datetime.now()
    search(driver, date = date)
    df = pd.DataFrame()
    while True:
        page_table_df = get_page_table(driver, table_class="table table-bordered table-striped table-hover sortable")
        df = pd.concat([df, page_table_df], ignore_index=True)  # Corrected line
        try:
            next_btn = driver.find_element(By.LINK_TEXT, 'Next')

            driver.execute_script("arguments[0].click();", next_btn)
        except NoSuchElementException:
            break
    print(f"Time taken to scrape: {datetime.now() - start_time}")    
    return df



def clean_df(df):
    new_df = df.drop_duplicates(keep='first') # Dropping Duplicates
    new_header = new_df.iloc[0] # grabing the first row for the header
    new_df = new_df[1:] # taking the data lower than the header row
    new_df.columns = new_header # setting the header row as the df header
    new_df.drop(["#"], axis=1, inplace=True)
    #converting string into float
    new_df['Rate']=new_df['Rate'].replace({',':""},regex=True).astype(float)
    new_df['Amount'] = new_df['Amount'].replace({',': ''}, regex=True).astype(float)
    return new_df


# Configure Edge options
options = Options()
options.headless = True  # Run in headless mode (no browser GUI)
options.add_argument("--disable-gpu")  # Improve performance in headless mode
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")


# Initialize the Edge WebDriver
driver = webdriver.Edge(service=Service(EdgeChromiumDriverManager().install()), options=options)

# Format today's date
current_day=datetime.now().strftime("%A").lower()
date = datetime.today().strftime('%m/%d/%Y')

stock_closed_day_list=['friday','saturday','sunday']

if current_day not in stock_closed_day_list:
    # Perform the search
    search(driver, date)
    df=scrape_data(driver,date)
    driver.quit()
else:
    print(f"Stock market is closed today ({current_day}). Execution terminated.")
    exit()



final_df=clean_df(df)


#creating the directory if it does not exist
if not os.path.exists('data'):
    os.makedirs('data')
file_name=date.replace("/","-")
final_df.to_csv(f"data/{file_name}.csv",index=False)