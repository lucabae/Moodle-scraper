from bs4 import BeautifulSoup as BS
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import requests
import dotenv
import os
import re
import time
import inquirer
from pathlib import Path

class Moodle_Scraper:
    
    def __init__(self):
        """
        Moodle_Scraper Class Constructor
            Builds the Moodle_Scraper object
            Needs .env file with "usuario" and "pw"
        """
        
        #user and password for Moodle
        self.user = dotenv.get_key(".env", "usuario")  
        self.pw = dotenv.get_key(".env", "pw")   
        
        # File system setup
        Path("downloads").mkdir(exist_ok=True)

        #FilePath setup
        self.course_path = ""
        self.section_path = ""
        
        #Selenium driver
        self.driver = self.setup_driver()
        
        #requests session
        self.session = requests.Session()
    
    def setup_driver(self):
        """
        Sets up the selenium Chrome driver
            Returns:
                None
        """
        
        options =  Options()
        
        options.add_experimental_option("prefs", {
            "download.prompt_for_download": False,       #dont ask for permission to download
            "plugins.always_open_pdf_externally": True,  # forces download
            "download.conflict_action": "overwrite"      #overwrites same name file 
        })
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--headless")
        
        return webdriver.Chrome(options=options)
    
    def login(self):
        """
        Logs into moodle.upm.es using selenium
        Extracts the cookies and sets up the requests session
            Returns:
                None
        """
        
        driver = self.driver
        user = self.user
        pw = self.pw
        
        if pw is None or user is None:
            raise Exception("No se pudo obtener el usuario y contraseña")
        
        #login
        url = "https://moodle.upm.es/titulaciones/oficiales/login/login.php"
        driver.get(url = url)
        driver.find_element(By.ID, "boton_cas").click()
        driver.find_element(By.ID, "username").send_keys(user)
        driver.find_element(By.ID, "password").send_keys(pw)
        driver.find_element(By.ID, "kc-login").click()
        WebDriverWait(driver, 30).until(
            EC.url_contains("moodle.upm.es/titulaciones/oficiales/my/")
        )
        
        #extract cookies and setup requests session
        self.cookies = driver.get_cookies()
        self.setup_session()
    
    def setup_session(self):
        """
        Sets up the requests session with the extracted cookies
        Extracts the session key
            Returns:
                None
        """
        
        for cookie in self.cookies:
            self.session.cookies.set(cookie["name"], cookie["value"], domain="moodle.upm.es")
        self.sesskey = self.driver.execute_script("return M.cfg.sesskey")
    
    def get_courses(self):
        """
        Extracts the course name and the URL
            Returns:
                dict{
                    course name : course URL
                    }
        """
        
        sesskey = self.sesskey
        session = self.session
        
        #extract the name of the courses and the URL
        url = f"https://moodle.upm.es/titulaciones/oficiales/lib/ajax/service.php?sesskey={sesskey}&info=core_course_get_enrolled_courses_by_timeline_classification"
        body = [{"index":0,"methodname":"core_course_get_enrolled_courses_by_timeline_classification","args":{"offset":0,"limit":24,"classification":"all","sort":"fullname","customfieldname":"","customfieldvalue":"","requiredfields":["id","fullname","shortname","showcoursecategory","showshortname","visible","enddate"]}}]
        response = session.post(url, json = body)
        json = response.json()
        courses = {}
        for course in json[0]["data"]["courses"]:
            courses[course["fullname"]] = course["viewurl"]
            
        #remove the Student Documentation
        courses.pop("Ayuda y documentación para estudiantes", None)
        
        self.courses = courses
        return courses
    
    def get_sections(self, course_url):
        """
        Extract the sections from the course
        Creates directories for each section
        Downloads the file in that directory
            Args:
                course_url: the URL for the course
            Returns:
                None
        """
        driver = self.driver
        course_path = self.course_path
        
        # get html for the course page
        driver.get(course_url)
        html = driver.page_source
        soup = BS(html, "html.parser")
        
        # get the sections, their names and create the directory
        secciones = soup.find_all("li", attrs={"data-for" : "section"})
        secciones_path = []
        secciones_validas = []
        i = 1
        for seccion in secciones:
            h3 = seccion.find("h3")
            if h3 == None:
                continue
            a = h3.find("a")
            if a == None:
                continue
            self.section_path = f"{i}.{a.text}".strip()
            i += 1
            
            # Construimos la ruta limpia dentro de "downloads/asignatura/seccion"
            directorio_final = Path("downloads") / self.clean_path(course_path) / self.clean_path(self.section_path)
            directorio_final.mkdir(parents=True, exist_ok=True)
            
            secciones_validas.append(seccion)
            # Guardamos la ruta absoluta como string
            secciones_path.append(str(directorio_final.resolve()))
        
        # scrape the files for each section
        i = 0    
        for seccion in secciones_validas:
            driver.execute_cdp_cmd("Page.setDownloadBehavior", {
                "behavior": "allow",
                "downloadPath": secciones_path[i]
            })
            self.download_files(seccion)
            self.download_wait(secciones_path[i], 30)
            i += 1

    def download_files(self, seccion):
        """
        Download the files
            Args:
                seccion: the section to scrape
            Returns:
                None
        """
        
        driver = self.driver  
        
        seccion_archivos = seccion.find_all("li", attrs={"data-for" : "cmitem"})
        for archivos in seccion_archivos:
            tag_descarga = archivos.find("a", onclick = True)
            if(tag_descarga != None and tag_descarga != ""):
                onclick = tag_descarga.get("onclick")
                if(onclick != None and onclick != ""):
                    link_descarga = re.search(r"'(https?://[^']+)'", tag_descarga.get("onclick")).group(1)
                    driver.get(link_descarga)
    
    def download_wait(self, path, timeout):
        """
        waits for the download in the current path to end
            Args:
                path: the path where the files are downloaded into
                
                timeout: how much time in seconds to wait
            Return:
                None 
        """
        
        sec = 0
        while sec < timeout:
            #checks if theres any file with .crdownload (chromiun temp download file)
            if not any(f.endswith(".crdownload") for f in os.listdir(path)):
                return
            else:
                sec += 1
                time.sleep(1)
        
    def scrape(self):
        """
        Calls all the functions to scrape moodle
            Returns:
                None
        """ 
        print("Iniciando sesión en Moodle...")
        self.login()
        
        print("Obteniendo cursos...")
        courses = self.get_courses()
        
        if not courses:
            print("No se encontraron cursos.")
            self.quit()
            return

        course_names = list(courses.keys())
        
        # TUI para elegir modo
        questions = [
            inquirer.List('mode',
                          message="¿Qué quieres descargar?",
                          choices=['Todo', 'Elegir asignaturas'],
                      ),
        ]
        answers = inquirer.prompt(questions)
        
        courses_to_scrape = {}

        if answers['mode'] == 'Todo':
            courses_to_scrape = courses
        else:
            # TUI para elegir asignaturas
            questions = [
                inquirer.Checkbox('selected_courses',
                                  message="Selecciona las asignaturas a descargar (Espacio para marcar, Enter para confirmar)",
                                  choices=course_names,
                                  ),
            ]
            answers = inquirer.prompt(questions)
            
            if not answers['selected_courses']:
                print("No se seleccionó ninguna asignatura. Saliendo.")
                self.quit()
                return
                
            for course_name in answers['selected_courses']:
                courses_to_scrape[course_name] = courses[course_name]

        for i, (course_name, course_url) in enumerate(courses_to_scrape.items()):
            print(f"Scraping course {i+1}/{len(courses_to_scrape)}: {course_name}")
            self.course_path = course_name.strip()
            self.get_sections(course_url)
            
        print("Éxito \n")
        time.sleep(10)
        self.quit()

    def quit(self):
        """
        Ends the selenium driver
            Returns:
                None
        """
        self.driver.quit()
    
    def clean_path(self, name):
        """
        Cleans the path String to a format accepted by Windows
        file system
            Args:
                name: the path string to clean
            Returns:
                Formatted string
        """
        return re.sub(r'[<>:"/|?*]', '', name).strip()

if __name__ == "__main__":
    scraper = Moodle_Scraper()
    scraper.scrape()