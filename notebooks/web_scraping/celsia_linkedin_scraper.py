from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import json
import csv

class LinkedInScraper:
    """
    Clase para extraer publicaciones de un perfil público de LinkedIn
    Requiere: 
    - ChromeDriver o GeckoDriver instalado
    - Suscripción a LinkedIn Premium (recomendado) para evitar bloqueos
    """
    
    def __init__(self, driver_path=None, headless=True):
        """
        Inicializa el scraper
        
        Args:
            driver_path (str): Ruta al driver del navegador
            headless (bool): Ejecutar en modo sin interfaz gráfica
        """
        self.driver = None
        self.setup_driver(driver_path, headless)
        
    def setup_driver(self, driver_path, headless):
        """Configura el driver de Selenium"""
        options = webdriver.ChromeOptions()
        
        if headless:
            options.add_argument('--headless')
        
        # Configuraciones para evitar detección
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        try:
            if driver_path:
                self.driver = webdriver.Chrome(executable_path=driver_path, options=options)
            else:
                self.driver = webdriver.Chrome(options=options)
            
            # Ejecutar script para evadir detección
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
        except Exception as e:
            print(f"Error configurando el driver: {e}")
            raise

    def scroll_page(self, scroll_pause_time=2):
        """
        Desplaza la página hasta el final para cargar todo el contenido
        
        Args:
            scroll_pause_time (int): Tiempo de pausa entre desplazamientos
        """
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        while True:
            # Desplazar hacia abajo
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause_time)
            
            # Calcular nueva altura
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def extract_post_data(self, post_element):
        """
        Extrae datos de una publicación individual
        
        Args:
            post_element: Elemento web de la publicación
            
        Returns:
            dict: Datos de la publicación
        """
        post_data = {}
        
        try:
            # Texto de la publicación
            text_element = post_element.find_element(By.CSS_SELECTOR, ".feed-shared-update-v2__description")
            post_data['text'] = text_element.text.strip() if text_element else ""
        except NoSuchElementException:
            post_data['text'] = ""
        
        try:
            # Fecha de la publicación
            date_element = post_element.find_element(By.CSS_SELECTOR, ".feed-shared-actor__sub-description")
            post_data['date'] = date_element.text.strip() if date_element else ""
        except NoSuchElementException:
            post_data['date'] = ""
        
        try:
            # Reacciones
            reactions_element = post_element.find_element(By.CSS_SELECTOR, ".social-details-social-counts__reactions-count")
            post_data['reactions'] = reactions_element.text.strip() if reactions_element else "0"
        except NoSuchElementException:
            post_data['reactions'] = "0"
        
        try:
            # Comentarios
            comments_element = post_element.find_element(By.CSS_SELECTOR, ".social-details-social-counts__comments")
            post_data['comments'] = comments_element.text.strip() if comments_element else "0"
        except NoSuchElementException:
            post_data['comments'] = "0"
        
        return post_data

    def scrape_profile_posts(self, profile_url, max_posts=50):
        """
        Extrae publicaciones de un perfil público de LinkedIn
        
        Args:
            profile_url (str): URL del perfil de LinkedIn
            max_posts (int): Número máximo de publicaciones a extraer
            
        Returns:
            list: Lista de diccionarios con datos de publicaciones
        """
        posts_data = []
        
        try:
            print(f"Navegando a: {profile_url}")
            self.driver.get(profile_url)
            
            # Esperar a que cargue la página
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".scaffold-layout__main"))
            )
            
            # Desplazar para cargar más publicaciones
            print("Cargando publicaciones...")
            self.scroll_page()
            
            # Localizar publicaciones
            posts = self.driver.find_elements(By.CSS_SELECTOR, ".feed-shared-update-v2")
            print(f"Encontradas {len(posts)} publicaciones")
            
            # Extraer datos de cada publicación
            for i, post in enumerate(posts[:max_posts]):
                print(f"Procesando publicación {i+1}/{min(len(posts), max_posts)}")
                
                try:
                    post_data = self.extract_post_data(post)
                    post_data['post_id'] = i + 1
                    posts_data.append(post_data)
                    
                    # Pausa para evitar ser bloqueado
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"Error extrayendo publicación {i+1}: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error durante el scraping: {e}")
        
        return posts_data

    def save_to_json(self, data, filename):
        """Guarda los datos en formato JSON"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Datos guardados en {filename}")

    def save_to_csv(self, data, filename):
        """Guarda los datos en formato CSV"""
        if not data:
            print("No hay datos para guardar")
            return
            
        keys = data[0].keys()
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(data)
        print(f"Datos guardados en {filename}")

    def close(self):
        """Cierra el driver del navegador"""
        if self.driver:
            self.driver.quit()
            print("Driver cerrado")

def main():
    """
    Función principal de ejemplo
    """
    # Configuración
    PROFILE_URL = "https://www.linkedin.com/company/celsiaenergia/"  # Reemplazar con URL real
    MAX_POSTS = 10
    DRIVER_PATH = None  # Ruta si ChromeDriver no está en PATH
    
    # Inicializar scraper
    scraper = LinkedInScraper(driver_path=DRIVER_PATH, headless=False)
    
    try:
        # Extraer publicaciones
        posts = scraper.scrape_profile_posts(PROFILE_URL, MAX_POSTS)
        
        if posts:
            print(f"\nExtraídas {len(posts)} publicaciones:")
            
            # Mostrar resumen
            for post in posts[:3]:  # Mostrar primeras 3
                print(f"\nPublicación {post['post_id']}:")
                print(f"Fecha: {post.get('date', 'N/A')}")
                print(f"Texto: {post.get('text', '')[:100]}...")
                print(f"Reacciones: {post.get('reactions', '0')}")
                print(f"Comentarios: {post.get('comments', '0')}")
            
            # Guardar datos
            scraper.save_to_json(posts, 'linkedin_posts.json')
            scraper.save_to_csv(posts, 'linkedin_posts.csv')
        else:
            print("No se encontraron publicaciones")
            
    except Exception as e:
        print(f"Error en la ejecución: {e}")
    
    finally:
        # Cerrar driver
        scraper.close()

if __name__ == "__main__":
    main()