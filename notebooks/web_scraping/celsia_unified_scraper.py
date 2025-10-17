"""
Scraper Unificado de Celsia - Combina el descubrimiento de secciones y la extracción detallada.
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import time
from datetime import datetime
from urllib.parse import urljoin

class UnifiedCelsiaScraper:
    """
    Una clase que encapsula toda la lógica de scraping para Celsia,
    desde el descubrimiento de URLs hasta la extracción de contenido detallado.
    """
    def __init__(self, delay=1.0):
        self.base_url = "https://www.celsia.com"
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'es-CO,es;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        })
        
        self.final_data = {
            'metadata': {
                'extraction_timestamp': datetime.now().isoformat(),
                'source_urls': [],
            },
            'results': {}
        }

    def safe_request(self, url, max_retries=3, timeout=15):
        """
        Realiza una solicitud HTTP de forma segura con reintentos y manejo de errores.
        """
        for attempt in range(max_retries):
            try:
                time.sleep(self.delay)
                print(f"[*] Obteniendo: {url} (Intento {attempt + 1})")
                response = self.session.get(url, timeout=timeout)
                response.raise_for_status()
                print(f"[+] Éxito: {len(response.text)} caracteres recibidos.")
                return response.text
            except requests.RequestException as e:
                print(f"[!] Error en intento {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    print(f"[X] Falló la solicitud para {url} después de {max_retries} intentos.")
                    return None

    def discover_sections(self):
        """
        Descubre las URLs de las secciones clave del sitio a partir de la página principal.
        """
        print("\n--- Fase 1: Descubriendo Secciones Clave ---")
        html = self.safe_request(self.base_url)
        if not html:
            print("[X] No se pudo acceder a la página principal. Abortando.")
            return {}

        soup = BeautifulSoup(html, 'lxml')
        links = soup.find_all('a', href=True)
        
        section_keywords = {
            'noticias': ['noticias', 'prensa', 'actualidad','sala-de-prensa'],
            'inversionistas': ['inversionistas', 'investors'],
            'quienes_somos': ['quienes-somos', 'la-nueva-era-de-la-energia', 'que-hacemos', 'se-parte-de-nuestro-equipo', 'fundacion', 'sostenibilidad', 'gobierno-corporativo'],
            'atencion_cliente': ['atencion-al-cliente', 'servicio-al-cliente', 'contacto', 'ayuda', 'reporta-un-dano','registra-tu-factura-digital', 'clientes/home-pqr'],
            'servicios_y_facturacion': ['servicios', 'soluciones', 'components/payments', 'paga-tus-facturas', 'internet.celsia.com'],
            'puntos_atencion': ['puntos-de-atencion', 'oficinas', 'encuentranos'],
        }

        found_sections = {key: [] for key in section_keywords}
        for section, keywords in section_keywords.items():
            for link in links:
                link_href = link.get('href', '').lower()
                if any(keyword in link_href for keyword in keywords):
                    full_url = urljoin(self.base_url, link['href'])
                    if full_url not in found_sections[section]:
                        found_sections[section].append(full_url)
        
        self.final_data['metadata']['source_urls'] = [self.base_url]
        print("[+] Secciones descubiertas.")
        return found_sections

    # --- MÉTODOS DE PROCESAMIENTO DETALLADO ---

    def process_noticias(self, urls):
        """
        Extrae todas las noticias de "sala de prensa" navegando a través de las páginas.
        """
        data = []
        processed_urls = set()
        base_news_url = "https://www.celsia.com/es/sala-de-prensa/"

        for page_num in range(1, 231): # Rango hasta 230
            paginated_url = f"{base_news_url}?current_paged={page_num}"
            print(f"\n--- Escaneando listado de noticias: {paginated_url} ---")

            list_html = self.safe_request(paginated_url)
            if not list_html:
                continue

            soup = BeautifulSoup(list_html, 'lxml')
            article_links = [a['href'] for a in soup.select('div.content-type-default-body a.item-new') if a.has_attr('href')]
            
            if not article_links:
                print(f"[!] No se encontraron más artículos en la página {page_num}. Finalizando búsqueda de noticias.")
                break
            
            print(f"[+] Se encontraron {len(article_links)} artículos en la página {page_num}.")

            for link in article_links:
                article_url = urljoin(base_news_url, link)
                if article_url in processed_urls:
                    continue
                processed_urls.add(article_url)
                
                print(f"    [*] Extrayendo noticia desde: {article_url}")
                article_html = self.safe_request(article_url)
                if not article_html:
                    data.append({'url': article_url, 'error': 'No se pudo acceder al artículo.'})
                    continue
                
                article_soup = BeautifulSoup(article_html, 'lxml')
                title = article_soup.find('h1').get_text(strip=True) if article_soup.find('h1') else 'No título'
                article_body = article_soup.find('div', class_='text-content')
                content = ' '.join(p.get_text(strip=True) for p in article_body.find_all(['p', 'ul'])) if article_body else 'No contenido.'
                
                data.append({'url': article_url, 'title': title, 'content': content})
        return data

    def process_quienes_somos(self, urls):
        """Extrae el texto principal de las páginas corporativas."""
        data = []
        for url in urls:
            html = self.safe_request(url)
            if not html:
                data.append({'url': url, 'error': 'No se pudo acceder a la página.'})
                continue

            soup = BeautifulSoup(html, 'lxml')
            title = soup.find('h1').get_text(strip=True) if soup.find('h1') else 'Sin título'
            main_content = soup.find('main') or soup
            text = ' '.join(p.get_text(strip=True) for p in main_content.find_all('p', limit=15))
            
            data.append({'url': url, 'page_title': title, 'summary': text})
            print(f"[*] Procesada página corporativa: {title}")
        return data

    def process_atencion_cliente(self, urls):
        """Conserva portales y extrae datos de contacto."""
        data = []
        for url in urls:
            if any(portal in url for portal in ['digiturno', 'clientes.celsia.com', 'nube.celsia.com']):
                purpose = "Portal de autogestión de clientes."
                data.append({'url': url, 'type': 'portal', 'description': purpose})
                print(f"[*] Enlace a portal conservado: {url}")
            else:
                html = self.safe_request(url)
                if not html:
                    data.append({'url': url, 'error': 'No se pudo acceder a la página.'})
                    continue

                soup = BeautifulSoup(html, 'lxml')
                title = soup.find('h1').get_text(strip=True) if soup.find('h1') else 'Sin título'
                text = ' '.join(p.get_text(strip=True) for p in soup.find('main').find_all('p')) if soup.find('main') else ''
                
                emails = list(set(re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', html)))
                phones = list(set(re.findall(r'01\s?8000[\s\d]+|\(\d+\)[\s\d-]+', html)))

                data.append({
                    'url': url, 'type': 'informational', 'page_title': title,
                    'summary': (text[:500] + '...') if len(text) > 500 else text,
                    'extracted_emails': emails, 'extracted_phones': phones
                })
                print(f"[*] Procesada página de atención al cliente: {title}")
        return data

    def process_generic_link(self, urls):
        """Función genérica para conservar enlaces importantes."""
        data = []
        for url in urls:
            description = "Enlace de interés general."
            if 'factura' in url or 'payment' in url:
                description = "Portal de pago de facturas."
            if 'internet.celsia.com' in url:
                description = "Página principal del servicio de Internet Celsia."
            if 'inversionistas' in url:
                description = "Portal para inversionistas."
            
            data.append({'url': url, 'description': description})
            print(f"[*] Enlace genérico conservado: {url}")
        return data

    def save_data(self, prefix="celsia_unified_data"):
        """Guarda los datos extraídos en un archivo JSON."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.final_data, f, ensure_ascii=False, indent=4)
        
        print(f"\n--- PROCESO COMPLETADO ---")
        print(f"[+] Todos los datos han sido guardados en: {filename}")

    def run(self):
        """
        Orquesta todo el proceso de scraping: descubrimiento, procesamiento y guardado.
        """
        try:
            # 1. Descubrir secciones
            sections = self.discover_sections()
            
            # Mapeo de secciones a funciones de procesamiento
            processors = {
                'noticias': self.process_noticias,
                'quienes_somos': self.process_quienes_somos,
                'inversionistas': self.process_generic_link,
                'atencion_cliente': self.process_atencion_cliente,
                'servicios_y_facturacion': self.process_generic_link,
                'puntos_atencion': self.process_generic_link,
            }
            
            print("\n--- Fase 2: Extracción de Datos Detallados ---")
            for section, urls in sections.items():
                if not urls:
                    print(f"\n--- Sin URLs para la sección: {section.upper()} ---")
                    continue
                
                print(f"\n--- Procesando sección: {section.upper()} ---")
                processor_func = processors.get(section, self.process_generic_link)
                section_data = processor_func(urls)
                self.final_data['results'][section] = section_data

            # 3. Guardar los datos
            self.save_data()

        except KeyboardInterrupt:
            print("\n[!] Proceso interrumpido por el usuario.")
            self.save_data("celsia_unified_data_interrupted")
        except Exception as e:
            print(f"\n[X] Ocurrió un error inesperado: {e}")
            import traceback
            traceback.print_exc()

def main():
    """Función principal para ejecutar el scraper unificado."""
    print("="*70)
    print("SCRAPER UNIFICADO DE CELSIA")
    print("="*70)
    
    scraper = UnifiedCelsiaScraper(delay=1.0)
    scraper.run()

if __name__ == "__main__":
    main()
