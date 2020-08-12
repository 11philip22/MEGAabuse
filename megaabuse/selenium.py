import chromedriver_autoinstaller

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities


class Selenium:
    def __init__(self):
        # Automatically install chromedriver
        chromedriver_autoinstaller.install()

        self.driver = webdriver.Chrome()
        self.driver.set_window_size(1288, 744)

    def login(self, username, password):
        self.driver.delete_all_cookies()

        self.driver.get("https://mega.nz/start")

        WebDriverWait(self.driver, 30).until(
            ec.visibility_of_element_located((By.LINK_TEXT, "Login")))
        self.driver.find_element(By.LINK_TEXT, "Login").click()
        self.driver.find_element(By.ID, "login-password").send_keys(password)
        self.driver.find_element(By.ID, "login-name").send_keys(username)
        self.driver.find_element(By.CSS_SELECTOR, ".height-32").click()

        WebDriverWait(self.driver, 30).until(
            ec.visibility_of_element_located((By.CSS_SELECTOR, ".affiliate-guide > .fm-dialog-close")))
        self.driver.find_element(By.CSS_SELECTOR, ".affiliate-guide > .fm-dialog-close").click()

        WebDriverWait(self.driver, 30).until(
            ec.visibility_of_element_located((By.CSS_SELECTOR, "#onboarding-dialog-how-to-upload > .close-button")))
        self.driver.find_element(By.CSS_SELECTOR, "#onboarding-dialog-how-to-upload > .close-button").click()

        WebDriverWait(self.driver, 30).until(
            ec.visibility_of_element_located((By.CSS_SELECTOR, "#onboarding-dialog-add-contacts > .close-button")))
        self.driver.find_element(By.CSS_SELECTOR, "#onboarding-dialog-add-contacts > .close-button").click()

    def import_(self, url):
        self.driver.get(url)
        WebDriverWait(self.driver, 30).until(
            ec.visibility_of_element_located((By.CSS_SELECTOR, ".fm-import-to-cloudrive > span")))
        self.driver.find_element(By.CSS_SELECTOR, ".fm-import-to-cloudrive > span").click()
        WebDriverWait(self.driver, 30).until(
            ec.visibility_of_element_located((By.CSS_SELECTOR, ".default-light-green-button")))
        self.driver.find_element(By.CSS_SELECTOR, ".default-light-green-button").click()

    def close(self):
        self.driver.quit()


# SEL = Selenium()
# SEL.login("7cqu8xk273jvcc57v0x2tjgp7gzobb@guerrillamailblock.com", "ZZUCdKHz1TsmjmShH2zbV")
# # SEL.close()
