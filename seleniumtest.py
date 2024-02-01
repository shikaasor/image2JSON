import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

browser = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

try:

    browser.get("http://localhost:8383/login")

    time.sleep(5)
    user_name = browser.find_element(By.XPATH, "//input[@type='text' and @class='form-control']")
    user_name.send_keys("guest@lamisplus.org")
    password = browser.find_element(By.XPATH, "//input[@type='password' and @class='form-control']")
    password.send_keys("123456")
    login = browser.find_element(By.XPATH, "//button[@type='submit' and @class='btn btn-primary btn-block']")
    login.click()
    time.sleep(2)
    HIV = browser.find_element(By.XPATH, "//span[@class='nav-text' and @title='HIV']")
    HIV.click()
    time.sleep(10)
except browser as e:
    print("An error occured:", e)