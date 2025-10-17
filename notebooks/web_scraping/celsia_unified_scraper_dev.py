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

    def process_noticias_celsia(self, url):
        """
        Extrae las noticias de las secciones Tolima y Valle del Cauca, incluyendo paginación,
        usando una arquitectura de dos fases y manejando múltiples grids por página.
        """
        print(f"\n--- Procesando Noticias Celsia desde: {url} ---")
        
        # --- FASE 1: Recolectar todos los artículos únicos ---
        all_articles = []
        processed_links = set()
        page_types = [("tolima", 6), ("valle-del-cauca", 12)]

        print("\n--- Fase 1: Recolectando todos los artículos únicos ---")
        for region, max_pages in page_types:
            for page_num in range(1, max_pages):
                page_url = f"{url}?{region}_current_paged={page_num}"
                print(f"    [*] Escaneando página: {page_url}")
                html = self.safe_request(page_url)
                if not html:
                    continue
                
                soup = BeautifulSoup(html, 'lxml')
                # SOLUCIÓN: Buscar TODOS los contenedores de grid, no solo el primero.
                grid_containers = soup.select('.grid-type-default')
                if not grid_containers:
                    continue

                # Iterar sobre cada contenedor de noticias encontrado (ej: uno para Tolima, uno para Valle)
                for container in grid_containers:
                    articles_on_page = container.find_all('a', class_='item-new')
                    for article_tag in articles_on_page:
                        link = urljoin(self.base_url, article_tag['href']) if article_tag.has_attr('href') else 'No Enlace'

                        if link in processed_links or link == 'No Enlace':
                            continue

                        processed_links.add(link)

                        title_tag = article_tag.select_one('.content-title.title-size-small')
                        title = title_tag.get_text(strip=True) if title_tag else 'No Título'

                        date_tag = article_tag.select_one('.content-date.title-size-extra-small')
                        date = date_tag.get_text(strip=True) if date_tag else 'No Fecha'

                        summary_tag = article_tag.select_one('.content-body.font-w-medium.color-primary')
                        summary = summary_tag.get_text(strip=True) if summary_tag else 'No Resumen'

                        all_articles.append({
                            'title': title,
                            'date': date,
                            'summary': summary,
                            'link': link
                        })

        # --- FASE 2: Clasificar la lista única de artículos ---
        print("\n--- Fase 2: Clasificando artículos recolectados ---")
        results = {
            "edicion_tolima": [],
            "edicion_valle": []
        }
        for article_data in all_articles:
            title_lower = article_data['title'].lower().strip()
            if title_lower.endswith('tolima'):
                results["edicion_tolima"].append(article_data)
            elif title_lower.endswith('valle') or title_lower.endswith('valle del cauca'):
                results["edicion_valle"].append(article_data)
            else:
                results["edicion_valle"].append(article_data)
        
        print(f"[+] Clasificación finalizada. Total Tolima: {len(results['edicion_tolima'])}. Total Valle: {len(results['edicion_valle'])}.")
        return results

    def process_revista_celsia(self, url):
        """
        Extrae el contenido de la página Revista Celsia, estructurado por secciones.
        """
        print(f"\n--- Procesando Revista Celsia desde: {url} ---")
        html = self.safe_request(url)
        if not html:
            return []

        soup = BeautifulSoup(html, 'lxml')
        sections = soup.select('section.cardsgrid-partial-e9ddf0')
        revista_data = []

        for section in sections:
            section_title_tag = section.select_one('.section__title')
            section_title = section_title_tag.get_text(strip=True) if section_title_tag else 'Sección sin título'
            print(f"    [*] Encontrada sección: {section_title}")

            section_items = []
            items = section.select('.section__cards_item_info')
            for item in items:
                h5_tag = item.select_one('h5')
                h5_text = h5_tag.get_text(strip=True) if h5_tag else ''

                p_tags = item.select('p')
                p_texts = ' '.join([p.get_text(strip=True) for p in p_tags])

                a_tag = item.select_one('a')
                link = urljoin(self.base_url, a_tag['href']) if a_tag and a_tag.has_attr('href') else 'No Enlace'

                section_items.append({
                    'title': h5_text,
                    'summary': p_texts,
                    'link': link
                })
            
            revista_data.append({
                'section_title': section_title,
                'items': section_items
            })

        return revista_data

    def process_sala_de_prensa_grid(self, url):
        """
        Extrae los enlaces principales del grid de la sala de prensa.
        """
        print(f"\n--- Procesando Grid de Sala de Prensa desde: {url} ---")
        html = self.safe_request(url)
        if not html:
            print(f"[X] No se pudo obtener el HTML de {url}")
            return []

        soup = BeautifulSoup(html, 'lxml')
        grid = soup.find('div', class_='content-custom-grid')
        
        if not grid:
            print("[!] No se encontró el div 'content-custom-grid'.")
            return []

        links = grid.find_all('a', href=True)
        extracted_links = []
        for link in links:
            full_url = urljoin(self.base_url, link['href'])
            extracted_links.append({
                'url': full_url,
                'text': link.get_text(strip=True)
            })
            print(f"    [*] Enlace de grid encontrado: {full_url}")
        
        return extracted_links

    # --- MÉTODOS DE PROCESAMIENTO DETALLADO ---

    def process_noticias(self, urls):
        """
        Extrae todas las noticias de "sala de prensa" navegando a través de las páginas.
        """
        data = []
        processed_urls = set()
        base_news_url = "https://www.celsia.com/es/sala-de-prensa/"

        for page_num in range(1, 2): # Rango hasta 230
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

            # 1.1. Procesar el grid específico de la sala de prensa
            sala_de_prensa_url = "https://www.celsia.com/es/sala-de-prensa/"
            grid_links = self.process_sala_de_prensa_grid(sala_de_prensa_url)
            if grid_links:
                self.final_data['results']['sala_de_prensa_grid'] = grid_links
                # Buscar la URL específica para las noticias celsia y procesarla
                noticias_celsia_url = next((item['url'] for item in grid_links if 'noticias-celsia' in item['url']), None)
                if noticias_celsia_url:
                    noticias_data = self.process_noticias_celsia(noticias_celsia_url)
                    self.final_data['results']['noticias_celsia'] = noticias_data
                
                # Buscar la URL específica para la revista celsia y procesarla
                revista_celsia_url = next((item['url'] for item in grid_links if 'revista-celsia' in item['url']), None)
                if revista_celsia_url:
                    revista_data = self.process_revista_celsia(revista_celsia_url)
                    self.final_data['results']['revista_celsia'] = revista_data

            
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
