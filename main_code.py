import cv2
import re
import requests
import time
import pandas as pd
from bs4 import BeautifulSoup
from pyzbar.pyzbar import decode

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

def extraer_carrefour(producto):
     '''
    Recibe el nombre de un producto para realizar la búsqueda en la página de carrefour,
    devuelve un diccionario con los resultados y sus precios.
    '''
    driver = webdriver.Chrome()

    driver.get(f'https://www.carrefour.es/?q={producto}')  #el driver accede al sitio web de carrefour con el producto buscado

    accept_cookies = driver.find_element(By.ID,'onetrust-accept-btn-handler')  #dentro de la web acepta las cookies
    accept_cookies.click()

    time.sleep(1) #espera 1s a que cargue la pagina
    soup = BeautifulSoup(driver.page_source, "html.parser") #convierte en sopa de html esa pagina
    productos = soup.find_all('h1',class_='ebx-result-title ebx-result__title') #busca los nombres de los productos
    precios= soup.find_all('p', class_='ebx-result-price ebx-result__price')  #busca los precios de los productos

    d={}
    driver.quit()
    for producto,precio in zip(productos,precios): #crea un diccionario de la forma {producto:precio}
        d[producto.text]=precio.text
    return d


def extraer_dia(producto):
    '''
    Recibe el nombre de un producto para realizar la búsqueda en la página de día,
    devuelve un diccionario con los resultados y sus precios.
    '''
    driver = webdriver.Chrome()
    driver.get(f'https://www.dia.es/search?q={producto}')
    time.sleep(1)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    productos = soup.find_all('p',class_='search-product-card__product-name')
    precios = soup.find_all('p',class_='search-product-card__active-price')

    d={}

    driver.quit()
    for producto,precio in zip(productos,precios):
        d[producto.text]=precio.text.replace('\xa0','')# se reemplaza el caracter del espacio
    return d
    

def descarte_marcas_blancas(texto, marca):
    '''
    Funcion que recibe una marca en formato str y devuleve un booleano marcando si es una marca blanca
    '''
        d_marcas_blancas = {'mercadona':'hacendado','carrefour':'carrefour','consum':'consum',
                            'el corte inglés':'el corte inglés','dia':'dia'}
        if marca in d_marcas_blancas:
            marca_blanca = d_marcas_blancas[marca]
            coincidencia = re.compile(fr'\b{marca_blanca}\b',re.IGNORECASE)
            if coincidencia.search(texto):
                return True
        return False

def read_barcodes(frame):
    '''
    Recibe un fotograma y trata de identificar y leer los posibles codifos de barra en formato utf-8.
    Devuelve la lectura y un booleano que afirma o desmiente la lectura.
    '''
    barcodes = decode(frame)
    for barcode in barcodes:
        barcode_data = barcode.data.decode('utf-8')
        barcode_type = barcode.type
        x, y, w, h = barcode.rect
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        # Mostrar información del código de barras
        text = f"{barcode_data} ({barcode_type})"
        print("[INFO] Encontrado {} código: {}".format(barcode_data, barcode_type))
        cv2.putText(frame, text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        if barcode_data is not None:
            return (barcode_data,True)
    return (None,False)

def realizar_consulta(codigo):
    '''
    Recibe un codigo de barra en forma numérica y de vuelve su marca
    y nombre de producto tras acceder por Webscraping
    '''
    url = f"https://go-upc.com/search?q={codigo}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text,'html.parser')
            return soup
        else:
            print(f"Error en la solicitud. Código de error: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Error en la solicitud: {e}")

def camara():
    '''
    Selección de la opción de cámara que abre la webcam y lee los posibles códigos
    que se presenten para extraer el número de la imagen.
    '''
    print("Has seleccionado la opción 1.")
    cap = cv2.VideoCapture(0)
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error al capturar el cuadro")
            break

        numero,barcode_detected = read_barcodes(frame)
        cv2.imshow('Barcode Scanner', frame)

        if barcode_detected:
            break

        if cv2.waitKey(1) & 0xFF == 27:  # Presiona Esc para salir
            break
    soup = realizar_consulta(numero)
    clase = soup.find('h1', class_='product-name')
    etiqueta_brand = soup.find('td',class_='metadata-label',string=re.compile(r'brand',re.IGNORECASE))
    if etiqueta_brand:
        brand = (etiqueta_brand.find_next_sibling('td')).get_text(strip=True) + ' '
    else:
        brand = ''
    if clase:
        producto = clase.text
        prefijo = 0
        for c_np, c_b in zip(producto, brand):
            if c_np == c_b:
                prefijo += 1
            else:
                break
        nombre_producto = producto[prefijo:]
    else:
        raise IndexError('No se encuentra el elemento escaneado')
    lista_super = ['mercadona','carrefour','consum','el corte inglés','dia']
    for super in lista_super:
        if descarte_marcas_blancas(producto, super):
            pass
    print(f'{brand}: {nombre_producto}')
    cap.release()
    cv2.destroyAllWindows()

    carre=extraer_carrefour('+'.join(nombre_producto.split()[:1]))
    dia=extraer_dia('+'.join(nombre_producto.split()[:1]))

    if len(carre)==0 and len(dia)==0:
        raise ValueError('El producto no se encuentra en estos supermercados')
    
    # Acortar los diccionarios a los primeros 5 elementos
    carre_acortado = {k: carre[k] for k in list(carre)[:5]}
    dia_acortado = {k: dia[k] for k in list(dia)[:5]}
    # Imprimir los diccionarios acortados
    create_supermarket_table(carre_acortado, dia_acortado)

def texto():
    '''
    Permite realizar las búsquedas de productos mediante una opción manual.
    '''
    print("Has seleccionado la opción 2.")
    producto=input('Introduzca el producto a buscar:')#solicita el producto al usuario
    carre=extraer_carrefour('+'.join(producto.split()))
    dia=extraer_dia('+'.join(producto.split()))
    
    if len(carre)==0 and len(dia)==0:
        raise ValueError('El producto no se encuentra en estos supermercados')
    # Acortar los diccionarios a los primeros 5 elementos
    carre_acortado = {k: carre[k] for k in list(carre)[:5]}
    dia_acortado = {k: dia[k] for k in list(dia)[:5]}
    # Imprimir los diccionarios acortados
    create_supermarket_table(carre_acortado, dia_acortado)

def create_supermarket_table(supermarket1, supermarket2):
    '''
    genera tablas para los distintos sumpermercados, dispone la información en las mismas
    '''
    # Convertir diccionarios a dataframes
    df1 = pd.DataFrame(list(supermarket1.items()), columns=['Producto', 'Precio en Carrefour'])
    df2 = pd.DataFrame(list(supermarket2.items()), columns=['Producto', 'Precio en DIA'])
    # Mostrar las tablas
    print(df1)
    print(df2)

def main():
    print("Bienvenido al buscador de productos")
    print("Por favor, selecciona una opción de busqueda:")
    print("1. Mediante Camara")
    print("2. Mediante Texto")

    opcion = input("Ingresa el número de la opción deseada (1 o 2): ")

    if opcion == '1':
        camara()
    elif opcion == '2':
        texto()
    else:
        print("Opción no válida. Por favor, ingresa 1 o 2.")

if __name__ == "__main__":
    main()
